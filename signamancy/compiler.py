import torch
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

from .registry import TokenRegistry, BlockType
from .parser import Rule, ParsedToken

@dataclass
class SparseMatrixData:
    """
    Raw data to construct a PyTorch Sparse Tensor.
    indices: [[Row(Rule)], [Col(Token)]]
    values: [Quantity]
    """
    indices: List[List[int]] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    shape: Tuple[int, int] = (0, 0)

@dataclass
class BlockKernels:
    """
    The physics matrices for a specific Memory Block (e.g., The Byte Block).
    """
    inputs: SparseMatrixData      # What is consumed/checked
    outputs: SparseMatrixData     # What is produced
    inhibitors: SparseMatrixData  # What must be absent (🚫)
    outputs_std: Optional[SparseMatrixData] = None  # StdDev for chaos ranges
    
    # New: consume-all inputs (X suffix) — subtract entire current value
    consume_all: Optional[SparseMatrixData] = None
    
    # For Byte Block only: Unit conversion lookup
    # Maps Token_Local_ID -> Parent_Token_Local_ID
    unit_map: Optional[torch.Tensor] = None 
    overflow_thresholds: Optional[torch.Tensor] = None

@dataclass
class KernelData:
    """
    The compiled cartridge ready for the Engine.
    """
    # Matrices per Block Type
    blocks: Dict[BlockType, BlockKernels]
    
    # Rule Metadata (aligned by Rule ID)
    # [Priority, Probability, MutexID, CPU_Flag]
    rule_meta: torch.Tensor 
    
    # Total counts for tensor sizing
    num_rules: int
    block_sizes: Dict[BlockType, int]

class SignamancyCompiler:
    def __init__(self, registry: TokenRegistry):
        self.registry = registry

    def compile(self, rules: List[Rule]) -> KernelData:
        """
        The Main Loop. Converts Rule Objects -> GPU Tensors.
        """
        # 1. Finalize Layout (Sort hot tokens to front)
        self.registry.compile_layout()
        
        # 2. Initialize Data Structures
        num_rules = len(rules)
        block_sizes = {
            bt: len(ids) for bt, ids in self.registry.export_layout().items()
        }
        
        # Storage for sparse data construction
        # Structure: data[BlockType][MatrixType] -> (indices, values)
        raw_data = {
            bt: {
                "in": [[], []], "in_val": [],
                "out": [[], []], "out_val": [],
                "out_std": [[], []], "out_std_val": [],
                "ban": [[], []], "ban_val": [],
                "all": [[], []], "all_val": []
            }
            for bt in BlockType
        }

        # Rule Metadata: [Priority, Probability, MutexID, CPU_Flag]
        meta_tensor = torch.zeros((num_rules, 4), dtype=torch.float32)

        # 3. Iterate Rules
        for r_idx, rule in enumerate(rules):
            # Metadata
            meta_tensor[r_idx, 0] = rule.priority
            meta_tensor[r_idx, 1] = rule.probability
            meta_tensor[r_idx, 2] = rule.mutual_exclusion_id if rule.mutual_exclusion_id else 0
            meta_tensor[r_idx, 3] = 1.0 if rule.requires_cpu else 0.0

            # Process Inputs
            for token in rule.inputs:
                self._add_entry(raw_data, r_idx, token, is_input=True)

            # Process Outputs
            for token in rule.outputs:
                self._add_entry(raw_data, r_idx, token, is_input=False)

        # 4. Construct Block Kernels
        final_blocks = {}
        
        for bt in BlockType:
            # Convert lists to SparseMatrixData
            # Input Matrix
            in_mat = self._build_sparse(
                raw_data[bt]["in"], raw_data[bt]["in_val"], (num_rules, block_sizes[bt])
            )
            # Output Matrix (mean)
            out_mat = self._build_sparse(
                raw_data[bt]["out"], raw_data[bt]["out_val"], (num_rules, block_sizes[bt])
            )
            # Output StdDev Matrix (optional)
            out_std_mat = None
            if raw_data[bt]["out_std_val"]:
                out_std_mat = self._build_sparse(
                    raw_data[bt]["out_std"], raw_data[bt]["out_std_val"], (num_rules, block_sizes[bt])
                )
            # Inhibitor Matrix
            ban_mat = self._build_sparse(
                raw_data[bt]["ban"], raw_data[bt]["ban_val"], (num_rules, block_sizes[bt])
            )
            # Consume-All Matrix
            all_mat = None
            if raw_data[bt]["all_val"]:
                all_mat = self._build_sparse(
                    raw_data[bt]["all"], raw_data[bt]["all_val"], (num_rules, block_sizes[bt])
                )
            
            # Unit Maps (Only for BYTE block)
            unit_map = None
            overflows = None
            if bt == BlockType.BYTE:
                unit_map, overflows = self._build_byte_lookups(block_sizes[bt])

            final_blocks[bt] = BlockKernels(
                inputs=in_mat,
                outputs=out_mat,
                inhibitors=ban_mat,
                outputs_std=out_std_mat,
                consume_all=all_mat,
                unit_map=unit_map,
                overflow_thresholds=overflows
            )

        return KernelData(
            blocks=final_blocks,
            rule_meta=meta_tensor,
            num_rules=num_rules,
            block_sizes=block_sizes
        )

    def _add_entry(self, data, rule_idx: int, token: ParsedToken, is_input: bool):
        """
        Helper to sort a token into the correct Block and Matrix.
        """
        # Resolve Global ID -> (BlockType, Local Index)
        b_type, local_id = self.registry.get_local_id(token.token_id)
        
        # Handle Quantity (Tuple range -> mean/std)
        val = token.quantity
        std_val = 0.0
        if isinstance(val, tuple):
            a, b = float(val[0]), float(val[1])
            mean = (a + b) / 2.0
            # Uniform distribution std ≈ (b - a) / sqrt(12)
            std_val = (b - a) / 3.46410161514
            val = mean

        # Determine which matrix (Input, Output, Inhibitor, Consume-All)
        if is_input:
            if token.consume_all:
                # Consume-All Matrix (binary flag)
                data[b_type]["all"][0].append(rule_idx)
                data[b_type]["all"][1].append(local_id)
                data[b_type]["all_val"].append(1.0)
            elif token.is_inhibitor:
                # Inhibitor Matrix
                data[b_type]["ban"][0].append(rule_idx)
                data[b_type]["ban"][1].append(local_id)
                data[b_type]["ban_val"].append(1.0)
            else:
                # Input (Consumption) Matrix
                data[b_type]["in"][0].append(rule_idx)
                data[b_type]["in"][1].append(local_id)
                data[b_type]["in_val"].append(val)
        else:
            # Output (Production) Matrix
            data[b_type]["out"][0].append(rule_idx)
            data[b_type]["out"][1].append(local_id)
            data[b_type]["out_val"].append(val)

            # Variance (only if we had a range)
            if std_val > 0.0:
                data[b_type]["out_std"][0].append(rule_idx)
                data[b_type]["out_std"][1].append(local_id)
                data[b_type]["out_std_val"].append(std_val)

    def _build_sparse(self, indices, values, shape) -> SparseMatrixData:
        if not values:
            return SparseMatrixData(shape=shape)
        return SparseMatrixData(indices=indices, values=values, shape=shape)


    def _build_byte_lookups(self, size: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Builds the lookup table for Carry-Lookahead logic.
        UnitMap[i] = Parent_Index_of_i (or -1 if none)
        """
        # Default -1 (No parent)
        unit_map = torch.full((size,), -1, dtype=torch.long)
        thresholds = torch.full((size,), 255, dtype=torch.int32)
        
        # Iterate tokens in BYTE block
        # We need to scan the registry to find which global IDs map to this block
        # This is slightly inefficient O(N), but done once at compile time.
        for meta in self.registry._tokens.values():
            if meta.block_type == BlockType.BYTE:
                local_id = meta.local_id
                
                # Set Threshold
                thresholds[local_id] = meta.overflow_threshold
                
                # Set Parent Link
                if meta.parent_unit_id is not None:
                    parent_meta = self.registry.get_metadata(meta.parent_unit_id)
                    if parent_meta and parent_meta.block_type == BlockType.BYTE:
                        unit_map[local_id] = parent_meta.local_id
                        
        return unit_map, thresholds
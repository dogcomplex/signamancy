from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Tuple
from enum import Enum

class BlockType(Enum):
    BIT = 1
    BYTE = 2
    FLOAT = 3

@dataclass
class ParsedToken:
    token_id: int
    quantity: Union[float, Tuple[float, float]] = 1.0
    is_inhibitor: bool = False 
    is_probability: bool = False
    probability_val: float = 1.0

@dataclass
class Rule:
    inputs: List[ParsedToken]
    outputs: List[ParsedToken]
    priority: int = 0
    mutual_exclusion_id: Optional[int] = None 
    probability: float = 1.0 
    is_init: bool = False
    requires_cpu: bool = False
    original_text: str = ""

@dataclass
class SparseMatrixData:
    indices: List[List[int]] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    shape: Tuple[int, int] = (0, 0)
    # For runtime torch construction
    mat: Optional[object] = None 

@dataclass
class BlockKernels:
    inputs: SparseMatrixData
    outputs: SparseMatrixData
    outputs_std: Optional[SparseMatrixData] = None
    inhibitors: SparseMatrixData
    unit_map: Optional[object] = None
    overflow_thresholds: Optional[object] = None

@dataclass
class KernelData:
    blocks: Dict[BlockType, BlockKernels]
    rule_meta: object # Tensor
    num_rules: int
    block_sizes: Dict[BlockType, int]
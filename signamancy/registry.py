# signamancy/registry.py
import hashlib
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple

class BlockType(Enum):
    BIT = 1   # 2-bit Flags (00/01/10/11). Dense packing.
    BYTE = 2  # uint8 Integers (0-255). Inventory math.
    FLOAT = 3 # float32. Continuous physics / Energy / Prices.

@dataclass
class TokenMetadata:
    original_text: str
    global_id: int       # 64-bit Hash (The Soul)
    block_type: BlockType
    
    # Thermodynamics
    is_chaotic: bool = False    # True = Needs 1024 particles. False = Global Constant.
    usage_count: int = 0        # For Huffman/Dense packing optimization.
    
    # Physical Location (Assigned during Compilation)
    local_id: Optional[int] = None 
    
    # Logic
    parent_unit_id: Optional[int] = None # For Carry-Lookahead
    overflow_threshold: int = 255

class TokenRegistry:
    def __init__(self):
        self._tokens: Dict[int, TokenMetadata] = {}
        self._lookup: Dict[str, int] = {}
        self._is_compiled = False

    def get_id(self, token_str: str) -> int:
        """Deterministic 64-bit hash."""
        if token_str in self._lookup:
            self._tokens[self._lookup[token_str]].usage_count += 1
            return self._lookup[token_str]
        
        token_bytes = token_str.encode('utf-8')
        # CityHash64 preferred, fallback to truncated SHA256
        hash_bytes = hashlib.sha256(token_bytes).digest()[:8]
        global_id = int.from_bytes(hash_bytes, byteorder='little', signed=False)
        return global_id

    def register(self, token_str: str, type_hint: BlockType = BlockType.BYTE) -> int:
        """
        Registers a token. Upgrades type if necessary. Increments usage.
        """
        global_id = self.get_id(token_str) # Increments usage if exists
        
        if global_id not in self._tokens:
            self._tokens[global_id] = TokenMetadata(
                original_text=token_str,
                global_id=global_id,
                block_type=type_hint,
                usage_count=1
            )
            self._lookup[token_str] = global_id
        else:
            # Type Escalation (Bit -> Byte -> Float)
            current = self._tokens[global_id]
            if type_hint.value > current.block_type.value:
                current.block_type = type_hint
                
        return global_id

    def mark_chaotic(self, token_id: int):
        """Flag token as requiring particle simulation."""
        if token_id in self._tokens:
            self._tokens[token_id].is_chaotic = True

    def compile_layout(self):
        """
        The 'Hallowing' Step. 
        Sorts tokens by Type and Frequency to generate optimal GPU indices.
        """
        # Separate by BlockType
        blocks = {t: [] for t in BlockType}
        for meta in self._tokens.values():
            blocks[meta.block_type].append(meta)
            
        # Sort each block by Usage (Descending) -> Hot tokens get low indices
        for b_type in blocks:
            blocks[b_type].sort(key=lambda x: x.usage_count, reverse=True)
            
            # Assign Local IDs
            for index, meta in enumerate(blocks[b_type]):
                meta.local_id = index

        self._is_compiled = True

    def get_local_id(self, global_id: int) -> Tuple[BlockType, int]:
        """Runtime lookup: Returns (Block, Index) for Tensor access."""
        if not self._is_compiled:
            raise RuntimeError("Registry not compiled. Call compile_layout() first.")
        meta = self._tokens[global_id]
        return (meta.block_type, meta.local_id)

    # --- Added: Introspection helpers used by parser/compiler/bridge ---
    def get_metadata(self, global_id: int) -> Optional[TokenMetadata]:
        return self._tokens.get(global_id)

    def resolve(self, global_id: int) -> str:
        meta = self._tokens.get(global_id)
        return meta.original_text if meta else str(global_id)

    def export_layout(self) -> Dict[BlockType, List[int]]:
        """
        Returns a mapping BlockType -> list of local indices (post-compile).
        Useful for sizing tensors.
        """
        if not self._is_compiled:
            self.compile_layout()
        layout: Dict[BlockType, List[int]] = {t: [] for t in BlockType}
        for meta in self._tokens.values():
            if meta.local_id is None:
                continue
            layout[meta.block_type].append(meta.local_id)
        return layout

    def register_unit_link(self, child_token: str, parent_token: str, threshold: int = 255) -> None:
        """
        Declare that 'child_token' overflows into 'parent_token' when it exceeds 'threshold'.
        Example: Potion -> Potion_Pack at threshold=9 (i.e., 10 Potions -> 1 Pack).
        """
        child_id = self.register(child_token, BlockType.BYTE)
        parent_id = self.register(parent_token, BlockType.BYTE)

        child_meta = self._tokens[child_id]
        child_meta.parent_unit_id = parent_id
        child_meta.overflow_threshold = int(threshold)
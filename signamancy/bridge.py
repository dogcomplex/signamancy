import torch
import numpy as np
from typing import Dict, Any, List, Union
from .registry import TokenRegistry, BlockType
from .engine import SignamancyEngine

class SignamancyBridge:
    """
    The Interface Layer. 
    Translates between Human Concepts (Strings/JSON) and GPU Tensors.
    """
    def __init__(self, engine: SignamancyEngine, registry: TokenRegistry):
        self.engine = engine
        self.registry = registry

    def get_state_snapshot(self, token_filter: List[str] = None) -> Dict[str, Any]:
        """
        Collapses the Quantum State (Particles) into Classical State (Mean/Variance).
        Returns a JSON-serializable dict for the UI.
        """
        snapshot = {}
        
        # 1. Identify which tokens to fetch
        # If filter is None, fetch everything (expensive!)
        # In practice, LOKI asks for specific 'View' tokens.
        
        for bt in BlockType:
            if bt not in self.engine.state: continue
            
            # Get raw tensor: [Batch, Num_Tokens]
            raw_data = self.engine.state[bt].float() # Cast to float for stats
            
            # Calculate Stats across the Batch Dimension (Dim 0)
            means = raw_data.mean(dim=0).cpu().numpy()
            stds = raw_data.std(dim=0).cpu().numpy()
            
            # Map back to strings
            # We need to iterate the registry to find which GlobalID maps to this LocalID
            # This is O(N_Tokens), acceptable for UI refresh rates (60Hz)
            
            # Optimization: The Registry should allow getting GlobalID from (Block, Local)
            # For now, we iterate:
            for gid, meta in self.registry._tokens.items():
                if meta.block_type == bt:
                    local_id = meta.local_id
                    if local_id is None: continue
                    
                    name = meta.original_text
                    
                    # Filter check
                    if token_filter and name not in token_filter:
                        continue
                        
                    val_mean = means[local_id]
                    val_std = stds[local_id]
                    
                    # Only include non-zero tokens to save bandwidth
                    if val_mean > 0.001 or val_mean < -0.001:
                        snapshot[name] = {
                            "val": float(round(val_mean, 3)),
                            "std": float(round(val_std, 3)) if val_std > 0 else 0.0,
                            "type": bt.name
                        }
                        
        return snapshot

    def inject_signal(self, token_str: str, quantity: float = 1.0, operation: str = "ADD"):
        """
        God Mode. Allows LOKI/User to manually modify the state.
        """
        gid = self.registry.get_id(token_str)
        meta = self.registry.get_metadata(gid)
        
        if not meta or meta.local_id is None:
            print(f"Warning: Token '{token_str}' not compiled into engine.")
            return

        bt = meta.block_type
        local_id = meta.local_id
        
        target_tensor = self.engine.state[bt]
        
        # Apply to ALL universes in the batch
        # We treat manual injection as a 'Global Truth' update
        if operation == "ADD":
            target_tensor[:, local_id] += quantity
        elif operation == "SET":
            target_tensor[:, local_id] = quantity
        elif operation == "SUB":
            target_tensor[:, local_id] -= quantity
            
        # Clamp if necessary (BYTE logic)
        if bt == BlockType.BYTE:
             self.engine.state[bt] = torch.clamp(target_tensor, 0, 255).to(torch.int16)

    def get_particle_distribution(self, token_str: str) -> List[float]:
        """
        Debug tool. Returns the raw particle values for a specific token.
        Useful for visualizing the probability cloud in LOKI.
        """
        gid = self.registry.get_id(token_str)
        meta = self.registry.get_metadata(gid)
        if not meta: return []
        
        raw = self.engine.state[meta.block_type][:, meta.local_id]
        return raw.cpu().numpy().tolist()
import re
import hashlib
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union
from .registry import TokenRegistry, BlockType

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
    # For 'One-Of' branching logic (A => B | C)
    mutual_exclusion_id: Optional[int] = None 
    probability: float = 1.0 
    is_init: bool = False
    requires_cpu: bool = False
    original_text: str = ""

class SignamancyParser:
    def __init__(self, registry: TokenRegistry):
        self.registry = registry
        # Regex: (Inhibitor?)(Symbol)(Quantity stuff)
        self.token_pattern = re.compile(r'^(🚫?)([^0-9%\-.]+)(.*)$')

    def parse_text(self, text: str) -> List[Rule]:
        rules = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "//")):
                continue
            
            # Strip comments
            clean_line = line.split("#")[0].strip()
            if not clean_line: continue

            # Expand sugar (A <=> B, A :> B)
            expanded = self._expand_sugar(clean_line)
            
            for exp in expanded:
                new_rules = self._parse_rule_logic(exp, original=line)
                rules.extend(new_rules)
        return rules

    def _expand_sugar(self, line: str) -> List[str]:
        if "<=>" in line:
            left, right = line.split("<=>")
            return [f"{left} => {right}", f"{right} => {left}"]
        
        if ":>" in line:
            # Property sugar: "Apple :> Seed Core" -> "=> Apple_Seed Apple_Core"
            # This defines existence/initialization of properties.
            parent, props = line.split(":>")
            parent = parent.strip()
            
            # Extract parent quantity if present to propagate? 
            # For now assuming simple definition.
            sub_tokens = []
            for p in props.split():
                p = p.strip()
                if not p: continue
                # If parent is "Apple", child becomes "Apple_Seed"
                # Note: The registry hashes "Apple_Seed" as a unique token.
                sub_tokens.append(f"{parent}_{p}")
            
            # Return as an initialization/definition rule
            return [f"=> {' '.join(sub_tokens)}"]

        return [line]

    def _parse_rule_logic(self, line: str, original: str) -> List[Rule]:
        if "=>" not in line: return []
        
        lhs_str, rhs_str = line.split("=>")
        
        # Priority Parsing
        priority = 0
        if "❗" in lhs_str:
            p_match = re.search(r'❗(\d*)', lhs_str)
            priority = int(p_match.group(1)) if p_match.group(1) else 1
            lhs_str = re.sub(r'❗\d*', '', lhs_str)

        # Initialization Check
        is_init = "🎬" in lhs_str

        # Parse Inputs
        inputs = [self._parse_token(t) for t in lhs_str.split()]
        
        # Branching Logic (Handle |)
        # "A => B | C" -> Splits into two rules with same Exclusion ID
        branch_groups = rhs_str.split("|")
        generated_rules = []
        
        # Generate a deterministic ID for this branch group
        mutex_id = None
        if len(branch_groups) > 1:
            mutex_id = int(hashlib.sha256(line.encode()).hexdigest()[:8], 16)

        for branch in branch_groups:
            outputs = [self._parse_token(t) for t in branch.split()]
            
            # Calculate Branch Probability
            # If tokens have probabilities (Apple%50), extract to rule level
            branch_prob = 1.0
            for out in outputs:
                if out.is_probability:
                    if isinstance(out.quantity, float):
                        branch_prob *= out.quantity
                        out.quantity = 1.0 # Reset token qty
            
            # CPU Check (Simple Heuristic)
            requires_cpu = any("🧮" in self.registry.resolve(t.token_id) for t in inputs + outputs)

            generated_rules.append(Rule(
                inputs=inputs,
                outputs=outputs,
                priority=priority,
                mutual_exclusion_id=mutex_id,
                probability=branch_prob,
                is_init=is_init,
                requires_cpu=requires_cpu,
                original_text=original
            ))
            
        return generated_rules

    def _parse_token(self, token_str: str) -> ParsedToken:
        match = self.token_pattern.match(token_str)
        if not match:
            # Fallback
            return ParsedToken(self.registry.register(token_str, BlockType.BIT))

        inhibitor_char, symbol, quant_str = match.groups()
        # Normalize: strip trailing underscores that are often separators before quantities,
        # and trim whitespace.
        symbol = symbol.rstrip("_").strip()
        is_inhibitor = bool(inhibitor_char)
        
        # Quantity Parsing
        quantity = self._parse_quantity(quant_str)
        
        # Type Inference
        is_prob = "%" in quant_str
        is_range = isinstance(quantity, tuple)
        
        type_hint = BlockType.BYTE
        if is_range or is_prob or (isinstance(quantity, float) and quantity % 1 != 0):
            type_hint = BlockType.FLOAT
        elif quantity == 1 and not is_inhibitor:
            type_hint = BlockType.BIT # Optimistic BIT hint
            
        token_id = self.registry.register(symbol, type_hint)
        
        # Chaos Flagging
        if is_prob or is_range:
            self.registry.mark_chaotic(token_id)

        return ParsedToken(
            token_id=token_id,
            quantity=quantity,
            is_inhibitor=is_inhibitor,
            is_probability=is_prob
        )

    def _parse_quantity(self, q_str: str) -> Union[float, Tuple[float, float]]:
        if not q_str: return 1.0
        q_str = q_str.replace("_", "")
        
        if "%" in q_str:
            return float(q_str.replace("%", "")) / 100.0
        
        if "-" in q_str:
            try:
                parts = q_str.split("-")
                return (float(parts[0]), float(parts[1]))
            except: pass
            
        multiplier = 1.0
        if q_str.lower().endswith("k"): multiplier = 1000.0; q_str = q_str[:-1]
        elif q_str.lower().endswith("m"): multiplier = 1000000.0; q_str = q_str[:-1]
        
        try:
            return float(q_str) * multiplier
        except:
            return 1.0
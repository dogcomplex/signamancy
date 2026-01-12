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
    # New flags
    is_independent: bool = False  # 🎲% marker: independent dice
    consume_all: bool = False     # X suffix on input: reduce to zero
    is_bare_probability: bool = False  # Bare '%' without digits

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
            
            # Strip comments: inline // then #
            clean_line = line.split("//")[0]
            clean_line = clean_line.split("#")[0].strip()
            if not clean_line: continue

            # Expand sugar (A <=> B, A :> B)
            expanded = self._expand_sugar(clean_line)
            
            for exp in expanded:
                new_rules = self._parse_rule_logic(exp, original=line)
                rules.extend(new_rules)

        # Post-process: Detect accumulator tokens (output-only, produced by multiple rules)
        # These should be BYTE, not BIT, to allow counting
        self._escalate_accumulator_tokens(rules)

        return rules

    def _escalate_accumulator_tokens(self, rules: List[Rule]) -> None:
        """
        Find tokens that are only produced (never consumed) by multiple rules.
        These are "accumulator" tokens that should be BYTE to allow counting.
        Example: 👑 (crown) is produced by each rent payment and should accumulate.
        """
        from collections import defaultdict

        input_tokens = set()
        output_counts = defaultdict(int)

        for rule in rules:
            # Track all input tokens (consumed)
            for inp in rule.inputs:
                if not inp.is_inhibitor:  # Inhibitors don't consume
                    input_tokens.add(inp.token_id)

            # Track output token production counts
            for out in rule.outputs:
                output_counts[out.token_id] += 1

        # Find tokens that are output-only AND produced by multiple rules
        for token_id, count in output_counts.items():
            if token_id not in input_tokens and count >= 2:
                # This is an accumulator token - escalate to BYTE
                meta = self.registry.get_metadata(token_id)
                if meta and meta.block_type == BlockType.BIT:
                    meta.block_type = BlockType.BYTE

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
        
        # If explicit branch groups exist, keep existing branch behavior
        if "|" in rhs_str:
            branch_groups = rhs_str.split("|")
            generated_rules: List[Rule] = []
            mutex_id = int(hashlib.sha256(line.encode()).hexdigest()[:8], 16) if len(branch_groups) > 1 else None
            for branch in branch_groups:
                outputs = [self._parse_token(t) for t in branch.split()]
                # Branch probability product (legacy behavior)
                branch_prob = 1.0
                for out in outputs:
                    if out.is_probability:
                        branch_prob *= float(getattr(out, "probability_val", 1.0))
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
        
        # No explicit '|': apply recipes.csv semantics
        raw_outputs = [self._parse_token(t) for t in rhs_str.split()]
        
        independent = [o for o in raw_outputs if o.is_probability and getattr(o, "is_independent", False)]
        linked = [o for o in raw_outputs if o.is_probability and not getattr(o, "is_independent", False)]
        nonprob = [o for o in raw_outputs if not o.is_probability]
        generated_rules: List[Rule] = []
        
        # 1) Independent tokens => separate rules, each with its own probability
        for out in independent:
            # Preserve original quantity (including ranges) for production
            out_i = ParsedToken(token_id=out.token_id, quantity=out.quantity)
            requires_cpu = any("🧮" in self.registry.resolve(t.token_id) for t in inputs + [out_i])
            generated_rules.append(Rule(
                inputs=inputs,
                outputs=[out_i],
                priority=priority,
                mutual_exclusion_id=None,
                probability=float(getattr(out, "probability_val", 1.0)),
                is_init=is_init,
                requires_cpu=requires_cpu,
                original_text=original
            ))
        
        # 2) Linked % tokens => one-of group (with implicit remainder no-op)
        if len(linked) >= 2:
            explicit = [o for o in linked if not getattr(o, "is_bare_probability", False)]
            bare = [o for o in linked if getattr(o, "is_bare_probability", False)]
            sum_p = sum(float(getattr(o, "probability_val", 0.0)) for o in explicit)
            mutex_id = int(hashlib.sha256((line+"__linked").encode()).hexdigest()[:8], 16)
            # Renormalize if >1.0
            renorm = 1.0
            if sum_p > 1.0 and sum_p > 0:
                renorm = 1.0 / sum_p
            # Explicit probabilities
            for out in explicit:
                p = float(getattr(out, "probability_val", 0.0)) * renorm
                # Preserve original quantity (including numeric multipliers and ranges)
                out_l = ParsedToken(token_id=out.token_id, quantity=out.quantity)
                requires_cpu = any("🧮" in self.registry.resolve(t.token_id) for t in inputs + [out_l] + nonprob)
                generated_rules.append(Rule(
                    inputs=inputs,
                    outputs=[out_l] + nonprob,
                    priority=priority,
                    mutual_exclusion_id=mutex_id,
                    probability=p,
                    is_init=is_init,
                    requires_cpu=requires_cpu,
                    original_text=original
                ))
            # Bare probabilities share remainder equally
            remainder = max(0.0, 1.0 - sum_p)
            share = (remainder / len(bare)) if bare else 0.0
            for out in bare:
                if share <= 0:
                    continue
                # Preserve original quantity for bare-probability tokens
                out_l = ParsedToken(token_id=out.token_id, quantity=out.quantity)
                requires_cpu = any("🧮" in self.registry.resolve(t.token_id) for t in inputs + [out_l] + nonprob)
                generated_rules.append(Rule(
                    inputs=inputs,
                    outputs=[out_l] + nonprob,
                    priority=priority,
                    mutual_exclusion_id=mutex_id,
                    probability=share,
                    is_init=is_init,
                    requires_cpu=requires_cpu,
                    original_text=original
                ))
            if (sum_p < 1.0) and not bare:
                # Implicit no-op branch
                requires_cpu = any("🧮" in self.registry.resolve(t.token_id) for t in inputs)
                generated_rules.append(Rule(
                    inputs=inputs,
                    outputs=[],
                    priority=priority,
                    mutual_exclusion_id=mutex_id,
                    probability=(1.0 - sum_p),
                    is_init=is_init,
                    requires_cpu=requires_cpu,
                    original_text=original
                ))
            return generated_rules
        
        # 3) Fallback: single rule (possibly with a single % gating all outputs)
        branch_prob = 1.0
        outputs = []
        for out in raw_outputs:
            if out.is_probability and not getattr(out, "is_independent", False):
                branch_prob *= float(getattr(out, "probability_val", 1.0))
                # Preserve original quantity (do not collapse to 1)
                outputs.append(ParsedToken(token_id=out.token_id, quantity=out.quantity))
            else:
                outputs.append(out)
        requires_cpu = any("🧮" in self.registry.resolve(t.token_id) for t in inputs + outputs)
        generated_rules.append(Rule(
            inputs=inputs,
            outputs=outputs,
            priority=priority,
            mutual_exclusion_id=None,
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
        # Normalize symbol, strip separators
        symbol = symbol.rstrip("_").strip()
        is_inhibitor = bool(inhibitor_char)

        # Preserve keycap digits as part of symbol: move leading keycap cluster from quantity back to symbol
        # Matches sequences like '🔟' or '1\uFE0F\u20E3' at the start of quant_str
        keycap_match = re.match(r'^(?:\U0001F51F|[0-9]\uFE0F\u20E3)+', quant_str)
        if keycap_match:
            symbol = (symbol + keycap_match.group(0)).strip()
            quant_str = quant_str[keycap_match.end():]

        # Extract optional probability suffix like "%20" even if combined with ranges
        prob_val = 1.0
        is_prob = False
        is_bare = False
        if "%" in quant_str:
            m = re.search(r"%(?P<pct>-?\d+(?:\.\d+)?)\s*$", quant_str)
            if m:
                try:
                    prob_val = float(m.group("pct")) / 100.0
                    is_prob = True
                    quant_str = quant_str[:m.start()] + quant_str[m.end():]
                except:
                    pass
            else:
                # Bare % (equal-share in linked groups)
                is_prob = True
                is_bare = True
                # strip the trailing % for quantity parsing
                quant_str = quant_str.replace("%", "").strip()
        else:
            is_bare = False
        
        # Independent marker: leading 🎲 combined with %
        is_indep = False
        if is_prob and symbol.startswith("🎲"):
            is_indep = True
            symbol = symbol[1:].strip()
        
        # All-of consumption marker: trailing X on symbol (inputs only)
        consume_all = False
        if symbol.endswith("X"):
            consume_all = True
            symbol = symbol[:-1].strip()
        
        # Quantity Parsing (remaining part may be empty or a range/number)
        # Track if quantity was explicitly specified (even "1") vs bare token
        has_explicit_quantity = bool(quant_str.strip())
        quantity = self._parse_quantity(quant_str)

        # Type Inference
        # Rule of thumb: Only default to BIT if NO explicit quantity was given.
        # Any explicit quantity (even "1") → BYTE, since it signals intent to count.
        is_range = isinstance(quantity, tuple)
        type_hint = BlockType.BYTE
        if is_range or (isinstance(quantity, float) and quantity % 1 != 0):
            type_hint = BlockType.FLOAT
        else:
            # Escalate to FLOAT if large integral quantity
            try:
                qv = float(quantity)
                if qv >= 256 and abs(qv - round(qv)) < 1e-9:
                    type_hint = BlockType.FLOAT
            except:
                pass
            # Only BIT if: bare token (no explicit quantity), quantity resolves to 1, not inhibitor
            if quantity == 1 and not is_inhibitor and not has_explicit_quantity:
                type_hint = BlockType.BIT
            
        token_id = self.registry.register(symbol, type_hint)
        
        # Chaos Flagging
        if is_prob or is_range:
            self.registry.mark_chaotic(token_id)

        return ParsedToken(
            token_id=token_id,
            quantity=quantity,
            is_inhibitor=is_inhibitor,
            is_probability=is_prob,
            probability_val=prob_val,
            is_independent=is_indep,
            consume_all=consume_all,
            is_bare_probability=is_bare
        )

    def _parse_quantity(self, q_str: str) -> Union[float, Tuple[float, float]]:
        if not q_str: return 1.0
        q_str = q_str.replace("_", "")
        
        # Probability literal only if '%' is followed by digits
        if "%" in q_str:
            m = re.search(r"%(?P<pct>-?\d+(?:\.\d+)?)\s*$", q_str)
            if m:
                return float(m.group("pct")) / 100.0
            # Bare '%' (no digits): ignore probability, treat as no quantity
            q_str = q_str.replace("%", "").strip()
            if not q_str:
                return 1.0
        
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
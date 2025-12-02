import re
from pathlib import Path
from typing import Dict, Tuple, List
import torch

from signamancy.registry import TokenRegistry, BlockType
from signamancy.engine import SignamancyEngine


class PolicyManager:
    def __init__(self):
        self.rule_desires: Dict[str, float] = {}
        self.token_desires: Dict[str, float] = {}
        self.targets: List[Tuple[str, float]] = []

    def load_sheet(self, path: Path):
        """
        Parse a simple '♥ policy sheet' with lines like:
          ❗ ♥ => ♥ID_Sell_Preserves_Pumpkin_1.2 ♥🍺⚙1.4 ♥💧0.3
          ⛳ => ⛳👑1.0 ⛳💰1.0
          ♥💲Merchant => ♥💰2.0
        We collect '♥ID_*_w' and '♥<prefix>w' and '⛳<prefix>w' entries.
        """
        txt = path.read_text(encoding="utf-8")
        for raw in txt.splitlines():
            line = raw.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            if "=>" not in line:
                continue
            _, rhs = line.split("=>", 1)
            tokens = [t.strip() for t in rhs.split() if t.strip()]
            for tok in tokens:
                if tok.startswith("⛳"):
                    # ⛳<prefix><weight>
                    pref, w = self._split_emoji_weight(tok[1:])  # drop ⛳
                    if pref:
                        self.targets.append((pref, w))
                elif tok.startswith("♥ID_"):
                    # ♥ID_Name_weight  (weight after last underscore)
                    m = re.match(r"^♥(ID_.+?)_([0-9.]+)$", tok)
                    if m:
                        rid = m.group(1)
                        w = float(m.group(2))
                        self.rule_desires[rid] = w
                elif tok.startswith("♥"):
                    # ♥<prefix><weight>
                    pref, w = self._split_emoji_weight(tok[1:])  # drop ♥
                    if pref:
                        self.token_desires[pref] = w

    def _split_emoji_weight(self, s: str) -> Tuple[str, float]:
        """
        Split a trailing numeric weight from an emoji/prefix string.
        e.g., '🍺⚙1.4' -> ('🍺⚙', 1.4), '💧0.3' -> ('💧', 0.3)
        Default weight=1.0 if none found.
        """
        m = re.match(r"^(.*?)([0-9.]+)$", s)
        if m:
            pref = m.group(1)
            w = float(m.group(2))
            return pref, w
        return s, 1.0

    def apply_to_engine(self, engine: SignamancyEngine, registry: TokenRegistry, rule_id_to_indices: Dict[str, List[int]], policy_gain: float = 1.0):
        """
        Build static rule bias vector from rule_desires (♥ID_*),
        and dynamic token desirability vector per block from token_desires (♥<prefix>).
        Apply both into engine via set_rule_biases(...) and apply_token_desires(...).
        """
        num_rules = engine.num_rules
        static_bias = torch.zeros(num_rules, dtype=torch.float32)
        # Rule-level desires -> static bias (use log-scale)
        for rid, w in self.rule_desires.items():
            idxs = rule_id_to_indices.get(rid, [])
            if not idxs and "#" not in rid:
                # If base ID, include all its branches
                base = rid
                for key, indices in rule_id_to_indices.items():
                    if key == base or key.startswith(base + "#"):
                        idxs += indices
            for i in idxs:
                static_bias[i] += float(torch.log(torch.tensor(w)))  # log(w)
        engine.set_rule_biases(static_bias.to(engine.device))

        # Token desires -> per-block logD
        desires_per_block: Dict[BlockType, torch.Tensor] = {}
        # init zero logD for each block
        for bt, bk in engine.kernel.block_sizes.items():
            desires_per_block[bt] = torch.zeros(bk, dtype=torch.float32)
        # fill from registry matches
        # registry._tokens: global_id -> metadata with original_text, block_type, local_id
        for gid, meta in registry._tokens.items():  # type: ignore[attr-defined]
            name = meta.original_text
            for pref, w in self.token_desires.items():
                if name.startswith(pref):
                    desires_per_block[meta.block_type][meta.local_id] = float(torch.log(torch.tensor(w)))
        engine.apply_token_desires(desires_per_block, gain=policy_gain)

    # Verifier ------------------------------------------------------------
    def verify_sheet(self, path: Path) -> List[str]:
        """
        Verify that policy rules do not produce or consume non-policy tokens.
        Allowed:
          - Policy tokens: start with '♥' or '⛳'.
          - Catalysts: non-policy tokens present identically on LHS and RHS.
          - Start tokens: 🎬 on LHS and 💫 on RHS are permitted.
        Returns a list of violation strings; empty means clean.
        """
        txt = path.read_text(encoding="utf-8")
        violations: List[str] = []
        allowed_exceptions = {"🎬", "💫"}
        for lineno, raw in enumerate(txt.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            if "=>" not in line:
                continue
            lhs, rhs = [p.strip() for p in line.split("=>", 1)]
            lhs_tokens = self._extract_tokens(lhs)
            rhs_tokens = self._extract_tokens(rhs)
            # Filter policy tokens and allowed exceptions
            lhs_np = [t for t in lhs_tokens if not (t.startswith("♥") or t.startswith("⛳") or t in allowed_exceptions)]
            rhs_np = [t for t in rhs_tokens if not (t.startswith("♥") or t.startswith("⛳") or t in allowed_exceptions)]
            # Compare as multisets
            all_keys = set(lhs_np) | set(rhs_np)
            bad = []
            for k in all_keys:
                if lhs_np.count(k) != rhs_np.count(k):
                    bad.append(k)
            if bad:
                violations.append(f"L{lineno}: non-policy delta tokens {bad} in '{line}'")
        return violations

    def _extract_tokens(self, side: str) -> List[str]:
        tokens: List[str] = []
        for tok in side.split():
            t = tok.strip()
            if not t:
                continue
            # ignore control markers
            if t in ("❗", "♥", "⛳"):
                continue
            # normalize: strip trailing numeric weight/quantity and trailing decorators
            t = re.sub(r"[0-9._]+$", "", t)
            t = t.rstrip("🎯X")
            tokens.append(t)
        return tokens

    # Refresh from snapshot ------------------------------------------------
    def apply_from_snapshot(self, engine: SignamancyEngine, registry: TokenRegistry, rule_id_to_indices: Dict[str, List[int]], snapshot: dict, policy_gain: float = 1.0):
        """
        Recompute and apply biases from current ♥ tokens in the snapshot.
        This does not re-run policy rules; it only reads their current outputs.
        - ♥ID_* tokens map to per-rule static bias (log w)
        - ♥<prefix> tokens map to per-token desirability (log w) via sparse matvec
        """
        num_rules = engine.num_rules
        static_bias = torch.zeros(num_rules, dtype=torch.float32, device=engine.device)
        # Rule-level desires
        for k, meta in snapshot.items():
            if not k.startswith("♥ID_"):
                continue
            w = float(meta.get("val", 1.0))
            rid = k[1:]  # drop leading heart
            idxs = rule_id_to_indices.get(rid, [])
            if not idxs and "#" not in rid:
                base = rid
                for key, indices in rule_id_to_indices.items():
                    if key == base or key.startswith(base + "#"):
                        idxs += indices
            if idxs:
                logw = float(torch.log(torch.tensor(max(w, 1e-6), device=engine.device)))
                for i in idxs:
                    static_bias[i] += logw
        engine.set_rule_biases(static_bias)

        # Token desires
        desires_per_block: Dict[BlockType, torch.Tensor] = {}
        for bt, bk in engine.kernel.block_sizes.items():
            desires_per_block[bt] = torch.zeros(bk, dtype=torch.float32, device=engine.device)
        for gid, meta_reg in registry._tokens.items():  # type: ignore[attr-defined]
            name = meta_reg.original_text
            for k, meta in snapshot.items():
                if not k.startswith("♥") or k.startswith("♥ID_") or k.startswith("♥💲"):
                    continue
                pref = k[1:]
                if name.startswith(pref):
                    w = float(meta.get("val", 1.0))
                    desires_per_block[meta_reg.block_type][meta_reg.local_id] = float(torch.log(torch.tensor(max(w, 1e-6), device=engine.device)))
        engine.apply_token_desires(desires_per_block, gain=policy_gain)

    # Exporter ------------------------------------------------------------
    def export_sheet(self, path: Path, rule_biases: torch.Tensor, id_to_indices: Dict[str, List[int]], snapshot: dict, targets: List[Tuple[str, float]]):
        lines: List[str] = []
        lines.append("🎬 => 💫 ♥ ⛳")
        # Aggregate rule biases by ID base
        id_weights: List[Tuple[str, float]] = []
        rb = rule_biases.detach().cpu()
        for rid, idxs in id_to_indices.items():
            if not idxs:
                continue
            mean_bias = float(rb[idxs].mean().item())
            w = float(torch.exp(torch.tensor(mean_bias)).item())
            if abs(w - 1.0) > 1e-3:
                id_weights.append((rid, w))
        # Token desires from snapshot (♥prefix with val != 1)
        tok_weights: List[Tuple[str, float]] = []
        for k, meta in snapshot.items():
            if k.startswith("♥") and not k.startswith("♥ID_") and not k.startswith("♥💲"):
                pref = k[1:]
                w = float(meta.get("val", 1.0))
                if abs(w - 1.0) > 1e-3:
                    tok_weights.append((pref, w))
        chunks: List[str] = []
        for rid, w in sorted(id_weights, key=lambda x: -abs(x[1] - 1.0))[:200]:
            chunks.append(f"♥{rid}_{w:.3f}")
        for pref, w in sorted(tok_weights, key=lambda x: -abs(x[1] - 1.0))[:200]:
            chunks.append(f"♥{pref}{w:.3f}")
        if chunks:
            lines.append("❗ ♥ => " + " ".join(chunks))
        if targets:
            tchunks = [f"⛳{p}{w:.3f}" for p, w in targets]
            lines.append("⛳ => " + " ".join(tchunks))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


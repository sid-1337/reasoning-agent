from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Atom:
    predicate: str
    arguments: tuple[str, ...]
    negated: bool = False

    def __str__(self) -> str:
        sign = "not " if self.negated else ""
        args = ", ".join(self.arguments)
        return f"{sign}{self.predicate}({args})"


@dataclass(frozen=True)
class HornRule:
    body: tuple[Atom, ...]
    head: Atom

    def __str__(self) -> str:
        return f"{', '.join(map(str, self.body))} -> {self.head}"


@dataclass
class KnowledgeBase:
    facts: set[Atom]
    rules: list[HornRule]


def make_knowledge_base(facts: Iterable[Atom], rules: Iterable[HornRule]) -> KnowledgeBase:
    return KnowledgeBase(set(facts), list(rules))


def unify(
    pattern: Atom,
    ground: Atom,
    bindings: Optional[dict[str, str]] = None,
) -> Optional[dict[str, str]]:
    result = dict(bindings or {})
    if pattern.predicate != ground.predicate or pattern.negated != ground.negated:
        return None
    if len(pattern.arguments) != len(ground.arguments):
        return None
    for term, value in zip(pattern.arguments, ground.arguments):
        if term.startswith("?"):
            if term in result and result[term] != value:
                return None
            result[term] = value
        elif term != value:
            return None
    return result


def _instantiate(atom: Atom, bindings: dict[str, str]) -> Optional[Atom]:
    arguments = []
    for term in atom.arguments:
        if term.startswith("?"):
            if term not in bindings:
                return None
            arguments.append(bindings[term])
        else:
            arguments.append(term)
    return Atom(atom.predicate, tuple(arguments), atom.negated)


def _body_bindings(body: tuple[Atom, ...], facts: set[Atom]):
    def visit(index: int, bindings: dict[str, str]):
        if index == len(body):
            yield bindings
            return
        for fact in facts:
            updated = unify(body[index], fact, bindings)
            if updated is not None:
                yield from visit(index + 1, updated)

    yield from visit(0, {})


def forward_chain(
    kb: KnowledgeBase,
    max_rounds: int = 1000,
) -> tuple[set[Atom], list[tuple[HornRule, Atom]]]:
    known = set(kb.facts)
    if any(term.startswith("?") for atom in known for term in atom.arguments):
        raise ValueError("Knowledge-base facts must be ground")

    trace: list[tuple[HornRule, Atom]] = []
    for _ in range(max_rounds):
        additions: dict[Atom, HornRule] = {}
        for rule in kb.rules:
            for bindings in _body_bindings(rule.body, known):
                conclusion = _instantiate(rule.head, bindings)
                if conclusion is not None and conclusion not in known:
                    additions.setdefault(conclusion, rule)
        if not additions:
            return known, trace

        for conclusion in sorted(additions, key=str):
            trace.append((additions[conclusion], conclusion))
        known.update(additions)

    raise RuntimeError(f"Forward chaining exceeded {max_rounds} rounds")

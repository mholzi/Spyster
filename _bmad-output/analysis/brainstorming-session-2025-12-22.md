---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: ['spyster-design.md']
session_topic: 'Spyster MVP Prioritization and Game Mechanics Innovation'
session_goals: 'Prioritize features for MVP v1.0, then explore unique mechanics to differentiate from Spyfall'
selected_approach: 'ai-recommended'
techniques_used: ['first-principles-thinking', 'resource-constraints', 'cross-pollination', 'concept-blending']
ideas_generated: ['confidence-betting', 'double-agent-spy-power', 'implementation-sequencing']
context_file: 'spyster-design.md'
status: 'completed'
---

# Brainstorming Session Results

**Facilitator:** Markusholzhaeuser
**Date:** 2025-12-22

## Session Overview

**Topic:** Spyster MVP Prioritization and Game Mechanics Innovation

**Goals:**
1. Distill comprehensive design document into shippable MVP (v1.0 vs later)
2. Explore creative mechanics that differentiate Spyster from Spyfall

### Context Guidance

Input: Detailed Spyster game design document covering:
- 6-phase game flow (Lobby, Roles, Questioning, Vote, Reveal, Scoring)
- 4+ content packs (Classic, Home, Sci-Fi, Fantasy, HA-Themed)
- Comprehensive scoring system with multiple win conditions
- Technical architecture (WebSocket, game state management)
- Neon Party UI theme (inherited from Beatify)
- Edge cases and rules for player counts, disconnections, voting

### Session Setup

**Approach Selected:** AI-Recommended Techniques
- Customized technique suggestions based on session goals
- Two-part session: MVP prioritization followed by mechanics innovation

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** MVP Prioritization + Game Mechanics Innovation

**Recommended Sequence:**

| Phase | Technique | Category | Purpose |
|-------|-----------|----------|---------|
| 1A | First Principles Thinking | creative | Identify irreducible core |
| 1B | Resource Constraints | structured | Force prioritization |
| 2A | Cross-Pollination | creative | Borrow from other domains |
| 2B | Concept Blending | creative | Create unique mechanics |

**AI Rationale:** Rich design doc needs distillation before innovation. Structured prioritization first establishes MVP boundaries, then creative techniques unlock differentiation.

---

## Part 1: MVP Prioritization

### First Principles Conclusion

**Decision:** Full design doc = MVP. No feature cuts.

**Implementation Sequence:**

| Phase | Build | Dependency |
|-------|-------|------------|
| 1 | Core Loop | Role assignment, questioning, basic reveal |
| 2 | Multiplayer | WebSocket sync, player sessions, lobby |
| 3 | Voting | Vote calling, tallying, majority logic |
| 4 | Scoring | Points, round tracking, leaderboard |
| 5 | Content | Location packs, role data loading |
| 6 | Polish | Timer, UI theme, accessibility, edge cases |
| 7 | Display | TV/tablet display view |

---

## Part 2: Mechanics Innovation

### Cross-Pollination Sources Explored

- Party games: Werewolf, Codenames, Jackbox, The Resistance
- Beyond games: Poker, Reality TV, Improv

### Selected Innovation: Confidence Betting

**Core Mechanic:** Players secretly bet 1-3 points on their vote being correct.

| Bet Level | Display | If Correct | If Wrong |
|-----------|---------|------------|----------|
| Hunch | 1 die | +1 | 0 |
| Sure | 2 dice | +3 | -1 |
| ALL IN | 3 dice | +6 | -3 |

**Design Decisions:**
- Spy bets on their accusation (can bluff to frame)
- Bets revealed all at once after votes (one dramatic moment)
- Must vote to bet (no abstain betting)

### Concept Blend: Double Agent (Spy Power)

> If spy goes ALL IN on an innocent player AND that player gets voted out = **+10 points**

**Strategic Impact:**
- Spy incentivized to accuse confidently
- Creates "too confident?" suspicion meta
- Huge risk/reward swing
- Adds psychological depth

---

## Session Outcomes

### Key Decisions

| Area | Decision |
|------|----------|
| MVP Scope | Full design doc, no cuts |
| Build Order | Core loop → Multiplayer → Voting → Scoring → Content → Polish |
| Differentiator #1 | Confidence Betting system |
| Differentiator #2 | Double Agent spy power |

### Ideas Generated

1. **Confidence Betting** - 3-tier risk/reward voting layer
2. **Double Agent** - Spy bonus for successful high-stakes frame
3. **Implementation sequencing** - 7-phase build order

### Ideas Noted (Not Selected)

- Role Powers (High Roller, Insurance Agent, Card Counter, Loan Shark)
- Confessionals / Prediction Logs
- Spy Peek / Sabotage abilities

---

## Next Steps

1. Update Spyster design doc with Confidence Betting + Double Agent mechanics
2. Proceed to PRD workflow to formalize requirements
3. Reference this brainstorm during Architecture phase for scoring system design

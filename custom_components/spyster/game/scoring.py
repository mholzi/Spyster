"""Scoring calculations for Spyster game (Story 5.7)."""
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .state import GameState

_LOGGER = logging.getLogger(__name__)

# Scoring constants (FR44, FR45, FR47)
POINTS_CORRECT_VOTE = {1: 2, 2: 4, 3: 6}
POINTS_INCORRECT_VOTE = {1: -1, 2: -2, 3: -3}
POINTS_DOUBLE_AGENT_BONUS = 10
POINTS_SPY_GUESS_CORRECT = 10
POINTS_SPY_GUESS_WRONG = -5


def calculate_vote_score(
    voted_for: str | None,
    actual_spy: str,
    confidence: int,
) -> tuple[int, str]:
    """
    Calculate points for a vote (FR44, FR45).

    Args:
        voted_for: Player name voted for
        actual_spy: Actual spy's name
        confidence: Confidence level (1, 2, or 3)

    Returns:
        (points, outcome) - points can be positive or negative
    """
    if voted_for is None:
        return 0, "abstained"

    is_correct = voted_for == actual_spy
    confidence = min(max(confidence, 1), 3)  # Clamp to 1-3

    if is_correct:
        points = POINTS_CORRECT_VOTE[confidence]
        outcome = "correct"
    else:
        points = POINTS_INCORRECT_VOTE[confidence]
        outcome = "incorrect"

    return points, outcome


def calculate_double_agent_bonus(
    spy_vote_target: str | None,
    convicted_player: str | None,
    spy_confidence: int,
    spy_name: str,
) -> int:
    """
    Calculate Double Agent bonus (FR47).

    The spy gets +10 if:
    - They voted (not guessed location)
    - They used ALL IN (confidence = 3)
    - They voted for an innocent player
    - That innocent player was convicted

    Args:
        spy_vote_target: Who the spy voted for (None if guessed location)
        convicted_player: Who was convicted
        spy_confidence: Spy's confidence level
        spy_name: Spy's name

    Returns:
        Bonus points (10 or 0)
    """
    # Spy must have voted (not guessed)
    if spy_vote_target is None:
        return 0

    # Spy must have used ALL IN
    if spy_confidence != 3:
        return 0

    # Spy must have voted for an innocent (not themselves)
    if spy_vote_target == spy_name:
        return 0

    # The person spy voted for must have been convicted
    if spy_vote_target != convicted_player:
        return 0

    _LOGGER.info("Double Agent bonus awarded to spy!")
    return POINTS_DOUBLE_AGENT_BONUS


def calculate_round_scores(game_state: "GameState") -> dict[str, dict[str, Any]]:
    """
    Calculate all scores for the round (Story 5.7).

    Args:
        game_state: Current game state with votes and results

    Returns:
        Dict of {player_name: {points, outcome, breakdown}}
    """
    scores: dict[str, dict[str, Any]] = {}
    spy_name = game_state._spy_name
    convicted = game_state.convicted_player

    # Handle spy guess case
    if game_state.spy_guess:
        return calculate_spy_guess_scores(game_state)

    # No conviction case (AC5)
    if convicted is None:
        _LOGGER.info("No conviction - round ends without resolution")
        for player_name in game_state.players.keys():
            scores[player_name] = {
                "points": 0,
                "outcome": "no_conviction",
                "breakdown": [],
            }
        return scores

    # Calculate each player's score
    for voter_name, vote_data in game_state.votes.items():
        target = vote_data.get("target")
        confidence = vote_data.get("confidence", 0)
        abstained = vote_data.get("abstained", False)

        if abstained:
            # Abstain = 0 points
            scores[voter_name] = {
                "points": 0,
                "outcome": "abstained",
                "breakdown": [{"type": "abstain", "points": 0}],
            }
            continue

        # Calculate vote score
        points, outcome = calculate_vote_score(target, spy_name, confidence)

        breakdown = [{
            "type": "vote",
            "target": target,
            "confidence": confidence,
            "points": points,
            "correct": outcome == "correct",
        }]

        # Check for Double Agent bonus (spy only)
        if voter_name == spy_name:
            bonus = calculate_double_agent_bonus(
                target, convicted, confidence, spy_name
            )
            if bonus > 0:
                points += bonus
                breakdown.append({
                    "type": "double_agent",
                    "points": bonus,
                })

        scores[voter_name] = {
            "points": points,
            "outcome": outcome,
            "breakdown": breakdown,
        }

    # Add players who didn't vote (weren't in votes dict)
    for player_name in game_state.players.keys():
        if player_name not in scores:
            scores[player_name] = {
                "points": 0,
                "outcome": "no_vote",
                "breakdown": [],
            }

    # Determine round winner
    spy_caught = convicted == spy_name

    _LOGGER.info(
        "Round scores calculated: spy_caught=%s, convicted=%s",
        spy_caught,
        convicted
    )

    return scores


def calculate_spy_guess_scores(game_state: "GameState") -> dict[str, dict[str, Any]]:
    """
    Calculate scores when spy guessed location.

    Args:
        game_state: Game state with spy guess

    Returns:
        Score dict
    """
    scores: dict[str, dict[str, Any]] = {}
    spy_name = game_state._spy_name
    guess = game_state.spy_guess
    correct = guess.get("correct", False) if guess else False

    for player_name in game_state.players.keys():
        if player_name == spy_name:
            # Spy scores based on guess
            if correct:
                scores[player_name] = {
                    "points": POINTS_SPY_GUESS_CORRECT,
                    "outcome": "spy_guess_correct",
                    "breakdown": [{"type": "location_guess", "correct": True, "points": POINTS_SPY_GUESS_CORRECT}],
                }
            else:
                scores[player_name] = {
                    "points": POINTS_SPY_GUESS_WRONG,
                    "outcome": "spy_guess_wrong",
                    "breakdown": [{"type": "location_guess", "correct": False, "points": POINTS_SPY_GUESS_WRONG}],
                }
        else:
            # Other players voted or abstained - process their votes
            if player_name in game_state.votes:
                vote = game_state.votes[player_name]
                if vote.get("abstained"):
                    scores[player_name] = {
                        "points": 0,
                        "outcome": "abstained",
                        "breakdown": [],
                    }
                else:
                    # Votes are irrelevant when spy guesses - no points
                    scores[player_name] = {
                        "points": 0,
                        "outcome": "spy_guessed",
                        "breakdown": [{"type": "spy_guessed", "points": 0}],
                    }
            else:
                scores[player_name] = {
                    "points": 0,
                    "outcome": "spy_guessed",
                    "breakdown": [],
                }

    return scores

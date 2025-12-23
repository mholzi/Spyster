# Story 8.1: Classic Location Pack Content

Status: completed

## Story

As a **player**,
I want **a variety of interesting locations with thematically appropriate roles**,
So that **the game feels complete, replayable, and engaging across multiple sessions**.

## Acceptance Criteria

1. **Given** the content directory, **When** `content/classic.json` is created, **Then** it contains at least 10 unique locations (per FR56) following the enriched schema from Architecture.

2. **Given** each location in the pack, **When** the content is reviewed, **Then** it has 6-8 associated roles (per FR57) with each role having a `hint` field for new players.

3. **Given** each location, **When** content is reviewed, **Then** it has a `flavor` text field for atmosphere display on host screen.

4. **Given** the Classic pack, **When** locations are listed, **Then** they include varied settings (e.g., Beach, Hospital, School, Restaurant, Airport, Casino, etc.) with thematically appropriate roles.

5. **Given** the location pack schema, **When** validated, **Then** each location has unique `id` fields and each role has unique `id` within its location.

6. **Given** the spy views the location list, **When** displaying locations, **Then** names are clear and distinct enough for the spy to identify the correct location from Q&A context.

## Tasks / Subtasks

- [x] Task 1: Create `content/classic.json` with schema-compliant structure (AC: 1, 5)
  - [x] 1.1: Define pack metadata (id, name, description, version)
  - [x] 1.2: Create JSON structure following enriched schema from Architecture
  - [x] 1.3: Ensure all `id` fields are snake_case and unique

- [x] Task 2: Create minimum 10 diverse locations (AC: 1, 4, 6)
  - [x] 2.1: Beach location with 7 roles
  - [x] 2.2: Hospital location with 7 roles
  - [x] 2.3: School location with 7 roles
  - [x] 2.4: Restaurant location with 7 roles
  - [x] 2.5: Airplane location with 7 roles
  - [x] 2.6: Casino location with 7 roles
  - [x] 2.7: Space Station location with 7 roles
  - [x] 2.8: Theater location with 7 roles
  - [x] 2.9: Bank location with 7 roles
  - [x] 2.10: Police Station location with 7 roles

- [x] Task 3: Add role hints for each role (AC: 2)
  - [x] 3.1: Write hints that help players understand their role context
  - [x] 3.2: Ensure hints don't reveal the location too obviously
  - [x] 3.3: Make hints useful for Q&A strategy

- [x] Task 4: Add flavor text for each location (AC: 3)
  - [x] 4.1: Write atmospheric descriptions for host display
  - [x] 4.2: Keep flavor text concise (1-2 sentences)

## Dev Notes

### Architecture Compliance

**File Location:** `custom_components/spyster/content/classic.json`

**Required Schema (from Architecture):**
```json
{
  "id": "classic",
  "name": "Classic",
  "description": "The original Spyfall locations",
  "version": "1.0.0",
  "locations": [
    {
      "id": "beach",
      "name": "The Beach",
      "flavor": "Sandy shores, crashing waves, and sun-soaked relaxation",
      "roles": [
        {"id": "lifeguard", "name": "Lifeguard", "hint": "You watch over swimmers from your elevated chair"},
        // ... 5-7 more roles
      ]
    }
    // ... 9 more locations
  ]
}
```

### Content Design Guidelines

**Location Selection Criteria:**
- Familiar to wide audience (not niche)
- Clear role differentiation possible
- Rich Q&A possibilities
- Visually distinct from other locations

**Role Design Criteria:**
- Thematically appropriate to location
- Different levels of "insider knowledge" for interesting Q&A
- Mix of obvious and subtle roles
- Hints should help players roleplay, not give away location

### Naming Conventions

- Location `id`: snake_case (e.g., `space_station`, `movie_studio`)
- Role `id`: snake_case (e.g., `ice_cream_vendor`, `flight_attendant`)
- Location `name`: Title case with article if natural (e.g., "The Beach", "Space Station")
- Role `name`: Title case (e.g., "Ice Cream Vendor", "Flight Attendant")

### Project Structure Notes

- File path: `custom_components/spyster/content/classic.json`
- This is the first location pack - sets the pattern for future packs
- JSON file loaded by `game/content.py` module (Story 8.2)
- **Dependency:** Story 8.2 must be complete for this content to be loadable at runtime

### Quality Checklist

Before marking complete, verify:
- [x] Minimum 10 locations with 6-8 roles each (10 locations, 7 roles each)
- [x] All `id` fields are snake_case and unique
- [x] All locations have `flavor` text for host display
- [x] All roles have `hint` text for player guidance
- [x] JSON validates against architecture schema
- [x] Location names are distinct enough for spy deduction

### References

- [Source: _bmad-output/architecture.md#Content Architecture] - Enriched schema definition
- [Source: _bmad-output/epics.md#Story 8.1] - Original acceptance criteria
- [Source: _bmad-output/project-context.md#File Organization] - Directory structure

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Created classic.json with 10 locations: Beach, Airplane, Casino, Hospital, Restaurant, School, Theater, Bank, Police Station, Space Station
- Each location has 7 roles with unique id, name, and hint fields
- Each location has flavor text for atmospheric host display
- All ids are snake_case and unique within their scope
- Pack includes diverse settings covering: leisure (beach), travel (airplane), entertainment (casino, theater), service (hospital, restaurant, bank), education (school), government (police station), and exploration (space station)

### File List

- [x] `custom_components/spyster/content/classic.json`

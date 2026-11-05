# Furnishing v1: Sam's brief (2026-10-25, night)

Starting point: git tag `stage-4-ground-complete` (model home_v7).

## Sam's words (verbatim)
"We will not furnish the whole house.  Lets choose the rooms we will furnish and add fixtures to.  Lets do the kitchen,
master bedroom and bathroom.  The entrance hallway and living room.  Also the area from which you exit to the patio in
the back yard.  Also maybe the area around the staircase and elevator tower - at least the third floor and the room
that you enter into when you reach the third floor"

## Sam, 2026-10-26 ~03:30 (verbatim), after run 1 (living + dining)
"ok. so the cli is logged in - you can continue with furnishing the other areas of the home.  mainly the kitchen
fixtures, cabinets, sink, appliances, faucets etc.  they should all be modern.  Also the bathroom fixtures, sink,
faucet, cabinet, shower etc should be modern.

You can continue with the cli and then the interior decorating

i will say good night now"

## Sam's list read against the model's rooms (Claude Code; CONFIRMED by Sam: "Yes, the bathroom is the en-suite. The list is right.")
Room names, floors and areas come from `design.json` and `addition.json`.
| Sam said | Room in the model | Floor | Area |
|---|---|---|---|
| kitchen | Kitchen (open to dining) | ground | 14.0 m2 |
| master bedroom | Main bedroom | first | 20.6 m2 |
| bathroom | En-suite (off the main bedroom, through the walk-in wardrobe side) | first | 8.8 m2 |
| entrance hallway | Entrance hall (with the main stair) | ground | 11.5 m2 |
| living room | Living (open plan) | ground | 28.2 m2 |
| the area you exit to the patio from | Dining (open plan): sliders D23 to the terrace (the living room's sliders D02 are covered above) | ground | 17.8 m2 |
| stair and lift tower, third floor | Stair tower, roof level + the glass roof walkway | roof | 9.4 m2 + 2.4 m2 (from the room boxes) |
| the room you enter on the third floor | Top room east (the walkway leads into it) | roof | 13.3 m2 (from the room box) |

Still open: whether the covered terrace itself gets furniture; whether the tower's lower floors and the link lobbies
get anything (Sam: "at least the third floor").

# navigation/

SPOT motion via Boston Dynamics' GraphNav. Holds the recorded map of the tour space, a wrapper that lets the rest of the codebase ask SPOT to go to a named waypoint, and notes on how the map was built.

## Files

| File | Purpose |
|---|---|
| [tour_nav.py](tour_nav.py) | `GraphNavWrapper` — the public API used elsewhere in the project. Also contains `GraphNavInterface`, a lightly-edited copy of the Boston Dynamics SDK example that drives the underlying gRPC calls. |
| [graph_nav_util.py](graph_nav_util.py) | Boston Dynamics utility helpers (waypoint short-code conversion, edge/waypoint pretty-printing, annotation-name resolution). Imported by `tour_nav.py`. |
| [maps/downloaded_graph/](maps/downloaded_graph/) | The recorded GraphNav map for the tour room: graph protobuf, waypoint snapshots, edge snapshots, anchors. **This is the map used at runtime.** |
| [maps/downloaded_graph backup/](maps/downloaded_graph%20backup/) | A backup copy of the map. Keep it until you trust the current map. |

## How it works

A small, static GraphNav map was recorded ahead of time. At runtime, the parser increments a `current_location_index` for every `walk_command`. That index maps to a waypoint ID on the recorded map, and `GraphNavWrapper` tells SPOT to walk there. SPOT handles its own local obstacle avoidance while staying on the recorded route.

### The recorded map

![Recorded map overview](https://github.com/user-attachments/assets/a03df5f5-0123-4fdc-944b-d8ce172fba78)

> Images load from GitHub — they won't render in a fully offline checkout.

The map is small on purpose (a single room demo):

- **1 anchor** at the start. For larger spaces, more anchors improve positional accuracy (see "Anchoring" below).
- **5 fiducials** around a square room — one on each wall plus one near the start.
- **2-3 waypoints between fiducials** so SPOT has somewhere to pause if the spot right next to a fiducial is blocked.

## `GraphNavWrapper` API

`GraphNavWrapper` lives in [tour_nav.py:611](tour_nav.py#L611). It hides the GraphNav SDK behind a single-method interface.

### Init flows

**Flow A — wrapper authenticates the robot itself.** Useful for standalone testing.

```python
G = GraphNavWrapper(map_path="navigation/maps/downloaded_graph")
# You'll be prompted for SPOT username + password during init.
G.navigate_to("waypoint_14")
```

**Flow B — caller authenticates first, then hands the robot in.** Use this from inside the main app, because something else has already done auth.

```python
import bosdyn.client

sdk = bosdyn.client.create_standard_sdk('GraphNavClient')
robot = sdk.create_robot("192.168.80.3")
bosdyn.client.util.authenticate(robot)
# ... whatever else the app does ...
G = GraphNavWrapper(robot=robot, map_path="navigation/maps/downloaded_graph")
G.navigate_to("waypoint_14")
```

### `navigate_to(waypoint, use_gps=False)`

Walks SPOT to the named waypoint. Acquires the lease, powers on motors if needed, sends the navigation command, and returns:

- `True` on success
- `False` if the lease is already held, or the GraphNav RPC throws

### Available waypoint names

The wrapper builds its waypoint map from the `annotations.name` of each waypoint in [maps/downloaded_graph](maps/downloaded_graph/) (see [tour_nav.py:648](tour_nav.py#L648)). For the current map those are:

```
waypoint_1
waypoint_2
...
waypoint_27
default
```

`default` is the name annotated on the map's starting waypoint. `waypoint_N` names follow the recording order — open the map in the Boston Dynamics map viewer if you need to see which `N` is which physical spot. For example, `waypoint_14` is the south-most waypoint in the current map:

![Waypoint 14 location](https://github.com/user-attachments/assets/8a6a9b90-f36b-4206-8151-480f821cd0e8)

## Recording a new map

This section is a quick orientation. The authoritative reference is Boston Dynamics' [GraphNav documentation](https://dev.bostondynamics.com/docs/concepts/autonomy/graphnav_tutorials).

### Concepts

**Waypoints** — IDs at points where SPOT takes a 3D "snapshot" of its surroundings. SPOT creates them automatically every ~2 m while recording (more often on curves). You can also force one with `CreateWaypoint` during recording — useful at spots where you want SPOT to pause for narration or perform an action.

**Edges** — directed connections between two waypoints. They store how to get from one to the other. Created automatically between adjacent waypoints, or manually with `CreateEdge`.

### Recording

Use the Boston Dynamics SDK example `recording_command_line` (in `python/examples/graph_nav_command_line/` in the SDK). Drive SPOT with the controller. The example menu lets you start recording, create named waypoints, close loops, download the map, etc. Save the downloaded map to `navigation/maps/your_map/` and update the `map_path` you pass into `GraphNavWrapper`.

### Map processing

SPOT records as a **chain topology** by default: a start, an end, and you traverse start → end. If you want SPOT to keep going past the end (e.g., a loop tour), you need a **loop closure**.

**Loop closure** happens automatically when SPOT sees the same fiducial twice, or when it walks under 50 m and ends up back where it started. Otherwise you can close the loop manually in the recording tool.

**Anchoring** maps a fiducial or waypoint to the global frame. Without explicit anchors, SPOT estimates position by dead reckoning from the start node, and accuracy degrades the farther it walks. The default anchor is at the start. For larger maps, add more anchors to maintain accuracy.

### Tips for good maps

- Bigger maps need more fiducials.
- Bigger maps need more anchors.
- Each floor needs at least one fiducial.
- Walk close to fiducials while recording — SPOT recognizes them better.
- Record multiple paths to important waypoints. GraphNav can then pick alternates if one path is blocked.

## Extension points

- **Wire `walk_command` to motion** — currently [../core/controller.py](../core/controller.py) only bumps `current_location_index` on a walk command. Pass a `GraphNavWrapper` into the controller from [../main.py](../main.py) and call `wrapper.navigate_to(f"waypoint_{index}")` (or look up the name from a route table).
- **Bigger maps** — record a longer route and drop it in `maps/`. See "Tips for good maps" above.
- **Multiple SPOTs on the same map** — out of scope today. Would require waypoint-level coordination so two SPOTs don't try to occupy the same waypoint at the same time.

## Related

- [../README.md](../README.md) — first-time setup.
- [../core/controller.py](../core/controller.py) — where the future walk-command hook lives.
- Boston Dynamics SDK docs: <https://dev.bostondynamics.com/>

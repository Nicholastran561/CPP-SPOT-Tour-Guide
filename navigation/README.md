## How to use `GraphNavWrapper(robot, map directory)`
```Python
G = GraphNavWrapper(robot, "navigation/maps/downloaded_graph")
G.navitage_to("waypoint_1")
```
The wrapper allows you either initialize the robot and pass it through or initialize it on initialization.
## How to use `navigate_to(waypoint)`
`navigate_to(waypoint)`
waypoint: can be filled with any of the following names.

Quick Example:
```python
navigate_to("waypoint_1")
```
### Waypoints
points along the static route around the room.

```
waypoint_1
waypoint_2
waypoint_3
...
waypoint_27
```
### Defaults
I think they're the starting points of the map.
```
default
```
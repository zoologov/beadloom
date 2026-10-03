package org.example.orchard.planner

import org.example.orchard.geo.Row
import org.example.orchard.geo.distance

/** Orders rows so that each next row is the nearest one not yet visited. */
class RoutePlanner {
    fun plan(start: Row, rows: List<Row>): List<Row> {
        val left = rows.toMutableList()
        val route = mutableListOf<Row>()
        var here = start
        while (left.isNotEmpty()) {
            val next = left.minBy { distance(here, it) }
            left.remove(next)
            route.add(next)
            here = next
        }
        return route
    }
}

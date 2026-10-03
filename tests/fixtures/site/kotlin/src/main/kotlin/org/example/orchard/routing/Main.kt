package org.example.orchard.routing

import org.example.orchard.geo.Row
import org.example.orchard.planner.RoutePlanner

fun main() {
    val rows = listOf(Row("pear-3", 3, 0), Row("pear-1", 1, 0), Row("apple-2", 2, 1))
    val route = RoutePlanner().plan(Row("gate", 0, 0), rows)
    println(route.joinToString(" -> ") { it.name })
}

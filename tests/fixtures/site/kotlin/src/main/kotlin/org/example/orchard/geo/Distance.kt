package org.example.orchard.geo

/** A row of trees, placed on a grid. */
data class Row(val name: String, val x: Int, val y: Int)

/** Steps between two rows, walking along the grid. */
fun distance(a: Row, b: Row): Int = kotlin.math.abs(a.x - b.x) + kotlin.math.abs(a.y - b.y)

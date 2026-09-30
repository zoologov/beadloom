package org.example.orchard.planner

import kotlin.test.Test
import kotlin.test.assertEquals
import org.example.orchard.geo.Row

class RoutePlannerTest {
    @Test
    fun visitsTheNearestRowFirst() {
        val route = RoutePlanner().plan(Row("gate", 0, 0), listOf(Row("far", 5, 0), Row("near", 1, 0)))
        assertEquals(listOf("near", "far"), route.map { it.name })
    }
}

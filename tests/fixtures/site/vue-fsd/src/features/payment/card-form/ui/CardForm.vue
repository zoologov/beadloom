<script setup lang="ts">
import { useCartStore } from '@/entities/cart'

import { useCardDetails } from '../model/card'

const cart = useCartStore()
const card = useCardDetails()
</script>

<template>
  <form>
    <input v-model="card.holder" placeholder="Name on the card" />
    <input v-model="card.number" placeholder="Card number" />
    <p>{{ cart.label }}</p>
  </form>
</template>

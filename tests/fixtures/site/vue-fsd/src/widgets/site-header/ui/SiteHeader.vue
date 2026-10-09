<script setup lang="ts">
import { useCartStore } from '@/entities/cart'
import { BaseButton } from '@shared/ui'

const cart = useCartStore()
</script>

<template>
  <header>
    <BaseButton :label="`Cart (${cart.count})`" />
  </header>
</template>

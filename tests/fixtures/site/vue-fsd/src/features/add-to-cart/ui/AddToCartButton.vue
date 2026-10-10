<script setup lang="ts">
import { BaseButton } from 'src/shared/ui'

import { useAddToCart } from '../model/useAddToCart'

const props = defineProps<{ slug: string }>()
const add = useAddToCart()
</script>

<template>
  <BaseButton label="Add to cart" @click="add(props.slug)" />
</template>

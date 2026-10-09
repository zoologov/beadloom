<script setup lang="ts">
import { formatMoney } from '@/shared/lib'

import type { Product } from '../api/productApi'

defineProps<{ product: Product }>()
</script>

<template>
  <article>{{ product.title }} {{ formatMoney(product.price) }}</article>
</template>

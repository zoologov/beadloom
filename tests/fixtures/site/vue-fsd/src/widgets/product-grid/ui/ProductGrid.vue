<script setup lang="ts">
import { ProductCard } from '@/entities/product'
import { useProductStore } from '@/entities/product/model/productStore'
import { AddToCartButton } from '@/features/add-to-cart'

const products = useProductStore()
</script>

<template>
  <section>
    <div v-for="item in products.items" :key="item.slug">
      <ProductCard :product="item" />
      <AddToCartButton :slug="item.slug" />
    </div>
  </section>
</template>

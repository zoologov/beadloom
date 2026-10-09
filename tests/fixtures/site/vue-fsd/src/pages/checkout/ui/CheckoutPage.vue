<script setup lang="ts">
import { useCartStore } from '@/entities/cart'
import { CouponField } from '@/features/apply-coupon'
import { SiteHeader } from '@/widgets/site-header'

const cart = useCartStore()
</script>

<template>
  <SiteHeader />
  <p>{{ cart.total }}</p>
  <CouponField />
</template>

<script setup lang="ts">
import { useCartStore } from '@/entities/cart'
import { CouponField } from '@/features/apply-coupon'
import { CardForm } from '@/features/payment/card-form'
import { PayButton } from '@/features/payment/pay-button'
import { SiteHeader } from '@/widgets/site-header'

const cart = useCartStore()
</script>

<template>
  <SiteHeader />
  <p>{{ cart.total }}</p>
  <CouponField />
  <CardForm />
  <PayButton />
</template>

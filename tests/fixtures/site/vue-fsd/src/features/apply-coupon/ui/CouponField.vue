<script setup lang="ts">
import { BaseButton } from '@/shared/ui'

import { applyCoupon } from '../model/coupon'
</script>

<template>
  <BaseButton label="Apply coupon" @click="applyCoupon('SPRING')" />
</template>

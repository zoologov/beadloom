<script setup lang="ts">
import { BaseButton } from '@/shared/ui'

import { pay } from '../model/pay'
</script>

<template>
  <BaseButton label="Pay" @click="pay()" />
</template>

import { Stack } from 'expo-router'

import { AppProviders } from '@/app'

export default function RootLayout() {
  return (
    <AppProviders>
      <Stack />
    </AppProviders>
  )
}

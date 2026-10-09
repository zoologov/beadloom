import { apiBase } from '../config'

export async function http<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`)
  return (await response.json()) as T
}

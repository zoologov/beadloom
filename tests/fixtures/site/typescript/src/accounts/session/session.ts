import { type User, userWithToken } from "../users/user.js";

export function callerOf(authorization: string): User | null {
  const token = authorization.replace(/^Bearer\s+/i, "");
  return userWithToken(token) ?? null;
}

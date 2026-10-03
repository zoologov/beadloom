export interface User {
  name: string;
  token: string;
}

const USERS: readonly User[] = [
  { name: "ranger-4", token: "t-4" },
  { name: "ranger-9", token: "t-9" },
];

export function userWithToken(token: string): User | undefined {
  return USERS.find((user) => user.token === token);
}

import { betterAuth } from 'better-auth'
import { Database } from 'bun:sqlite'

export const auth = betterAuth({
  database: new Database('./dev.db'),
  emailAndPassword: { enabled: true, minPasswordLength: 6 },
  user: {
    additionalFields: {
      institution: { type: 'string', required: false, defaultValue: '' },
      role:        { type: 'string', required: false, defaultValue: 'analyst' },
    },
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
  },
})

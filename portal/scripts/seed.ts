// Run once after `bun db:migrate` to create mock users in dev.db
// Usage: bun db:seed
import { auth } from '../src/lib/auth'

const MOCK_USERS = [
  { email: 'analyst@farmtrust.eg', password: 'demo123', name: 'Ahmed Hassan',   institution: 'Banque Misr',        role: 'analyst' },
  { email: 'admin@farmtrust.eg',   password: 'demo123', name: 'Sara El-Sayed',  institution: 'FarmTrust',          role: 'admin'   },
  { email: 'reviewer@ncb.eg',      password: 'demo123', name: 'Khaled Ibrahim', institution: 'National Bank Egypt', role: 'analyst' },
]

for (const user of MOCK_USERS) {
  const result = await auth.api.signUpEmail({
    body: {
      email:       user.email,
      password:    user.password,
      name:        user.name,
      institution: user.institution,
      role:        user.role,
    },
  })
  if ('error' in result && result.error) {
    console.log(`Skip ${user.email} — may already exist`)
  } else {
    console.log(`Created ${user.email}`)
  }
}

console.log('Seed complete.')
process.exit(0)

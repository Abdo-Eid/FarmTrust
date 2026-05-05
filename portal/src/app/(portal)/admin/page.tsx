'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import * as Dialog from '@radix-ui/react-dialog'
import { formatDistanceToNow, parseISO } from 'date-fns'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

const MOCK_USERS = [
  { id: '1', name: 'Ahmed Hassan', email: 'analyst@farmtrust.eg', institution: 'FarmTrust', role: 'analyst', status: 'active', last_login: '2024-12-10T09:23:00Z' },
  { id: '2', name: 'Sara Mahmoud', email: 'admin@farmtrust.eg', institution: 'FarmTrust', role: 'admin', status: 'active', last_login: '2024-12-11T14:05:00Z' },
  { id: '3', name: 'Karim Nasser', email: 'reviewer@ncb.eg', institution: 'NCB Egypt', role: 'analyst', status: 'active', last_login: '2024-12-09T11:30:00Z' },
  { id: '4', name: 'Mona Fathi', email: 'mona.f@bankalex.eg', institution: 'Bank of Alexandria', role: 'analyst', status: 'active', last_login: '2024-12-08T16:45:00Z' },
  { id: '5', name: 'Youssef Gamal', email: 'y.gamal@bankalex.eg', institution: 'Bank of Alexandria', role: 'analyst', status: 'suspended', last_login: '2024-11-20T08:15:00Z' },
  { id: '6', name: 'Nadia Sami', email: 'n.sami@cib.eg', institution: 'CIB Egypt', role: 'analyst', status: 'active', last_login: '2024-12-07T10:00:00Z' },
]

const inviteSchema = z.object({
  fullName: z.string().min(1, 'Full name is required'),
  email: z.string().email('Invalid email address'),
  institution: z.string().min(1, 'Institution is required'),
  role: z.enum(['analyst', 'admin']),
})

type InviteFormData = z.infer<typeof inviteSchema>

export default function AdminPage() {
  const [activeSection, setActiveSection] = useState<'users' | 'api' | 'system'>('users')
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null)
  const [testConnectionResult, setTestConnectionResult] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
  })

  const onInviteSubmit = (data: InviteFormData) => {
    setInviteSuccess(`Invitation sent to ${data.email}`)
    reset()
    setTimeout(() => {
      setInviteOpen(false)
      setInviteSuccess(null)
    }, 1500)
  }

  const handleTestConnection = () => {
    setTestConnectionResult('✓ Mock API responding (12ms)')
    setTimeout(() => setTestConnectionResult(null), 3000)
  }

  const handleSuspendUser = (email: string) => {
    alert(`Action simulated: Suspend user ${email}`)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <PageHeader
        title="System Administration"
        subtitle="User management and system configuration"
      />

      <div className="flex gap-0">
        {/* Left Sub-Nav */}
        <div className="w-48 bg-white border-r border-gray-200 sticky top-0 h-screen">
          <nav className="py-4">
            {[
              { id: 'users', label: 'User Management', icon: 'group' },
              { id: 'api', label: 'API Configuration', icon: 'api' },
              { id: 'system', label: 'System Info', icon: 'monitor_heart' },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id as typeof activeSection)}
                className={`w-full flex items-center gap-2 px-4 py-3 text-sm cursor-pointer transition-colors ${
                  activeSection === item.id
                    ? 'bg-teal-50 text-teal-700 border-r-2 border-teal-600 font-medium'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <span className="material-symbols-outlined text-base">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Right Content */}
        <div className="flex-1 p-6">
          {activeSection === 'users' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-gray-900">Users ({MOCK_USERS.length})</h2>
                <Dialog.Root open={inviteOpen} onOpenChange={setInviteOpen}>
                  <Dialog.Trigger asChild>
                    <Button size="sm" variant="primary">
                      Invite User
                    </Button>
                  </Dialog.Trigger>
                  <Dialog.Portal>
                    <Dialog.Overlay className="fixed inset-0 bg-black/40" />
                    <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-md shadow-xl p-6 w-96">
                      <div className="flex items-center justify-between mb-4">
                        <Dialog.Title className="text-lg font-semibold text-gray-900">
                          Invite New User
                        </Dialog.Title>
                        <Dialog.Close asChild>
                          <button className="text-gray-500 hover:text-gray-700">
                            <span className="material-symbols-outlined">close</span>
                          </button>
                        </Dialog.Close>
                      </div>

                      <form onSubmit={handleSubmit(onInviteSubmit)} className="space-y-4">
                        {inviteSuccess && (
                          <div className="bg-green-50 border border-green-200 rounded-md p-3 text-sm text-green-800">
                            {inviteSuccess}
                          </div>
                        )}

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Full Name
                          </label>
                          <input
                            {...register('fullName')}
                            type="text"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                            placeholder="e.g. John Smith"
                          />
                          {errors.fullName && (
                            <p className="text-xs text-red-600 mt-1">{errors.fullName.message}</p>
                          )}
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Email
                          </label>
                          <input
                            {...register('email')}
                            type="email"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                            placeholder="e.g. user@bank.eg"
                          />
                          {errors.email && (
                            <p className="text-xs text-red-600 mt-1">{errors.email.message}</p>
                          )}
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Institution
                          </label>
                          <input
                            {...register('institution')}
                            type="text"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                            placeholder="e.g. NCB Egypt"
                          />
                          {errors.institution && (
                            <p className="text-xs text-red-600 mt-1">{errors.institution.message}</p>
                          )}
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Role
                          </label>
                          <select
                            {...register('role')}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                          >
                            <option value="analyst">Analyst</option>
                            <option value="admin">Admin</option>
                          </select>
                          {errors.role && (
                            <p className="text-xs text-red-600 mt-1">{errors.role.message}</p>
                          )}
                        </div>

                        <div className="flex gap-2 pt-4">
                          <Button type="submit" variant="primary" className="flex-1">
                            Send Invite
                          </Button>
                          <Dialog.Close asChild>
                            <Button type="button" variant="ghost" className="flex-1">
                              Cancel
                            </Button>
                          </Dialog.Close>
                        </div>
                      </form>
                    </Dialog.Content>
                  </Dialog.Portal>
                </Dialog.Root>
              </div>

              <Card padding="none">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-semibold text-gray-900">Name</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-900">Email</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-900">Institution</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-900">Role</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-900">Status</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-900">Last Login</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {MOCK_USERS.map((user) => (
                      <tr key={user.id} className="border-t border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-900">{user.name}</td>
                        <td className="px-4 py-3 text-gray-600">{user.email}</td>
                        <td className="px-4 py-3 text-gray-600">{user.institution}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                              user.role === 'admin'
                                ? 'bg-teal-100 text-teal-800'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                              user.status === 'active'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {user.status.charAt(0).toUpperCase() + user.status.slice(1)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {formatDistanceToNow(parseISO(user.last_login), { addSuffix: true })}
                        </td>
                        <td className="px-4 py-3">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleSuspendUser(user.email)}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            Suspend
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          )}

          {activeSection === 'api' && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Backend Connection</CardTitle>
                </CardHeader>
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2 block">
                      API Base URL
                    </label>
                    <code className="block bg-gray-100 rounded-md p-3 text-sm text-gray-800 font-mono">
                      {process.env.NEXT_PUBLIC_API_BASE || '/api'}
                    </code>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2 block">
                      Environment
                    </label>
                    <code className="block bg-gray-100 rounded-md p-3 text-sm text-gray-800 font-mono">
                      Development (Mock Mode)
                    </code>
                  </div>
                </div>
              </Card>

              <Card className="bg-amber-50 border-amber-200">
                <div className="flex gap-3">
                  <span className="material-symbols-outlined text-amber-600 flex-shrink-0 mt-0.5">
                    info
                  </span>
                  <div>
                    <p className="text-sm text-amber-800">
                      Set <code className="font-mono bg-amber-100 px-1 rounded">NEXT_PUBLIC_API_BASE</code> in{' '}
                      <code className="font-mono bg-amber-100 px-1 rounded">.env.local</code> to point to your
                      FastAPI backend. Currently using mock Route Handlers.
                    </p>
                  </div>
                </div>
              </Card>

              <div className="flex gap-2">
                <Button variant="secondary" onClick={handleTestConnection}>
                  Test Connection
                </Button>
                {testConnectionResult && (
                  <div className="flex items-center text-sm text-green-700 font-medium">
                    {testConnectionResult}
                  </div>
                )}
              </div>

              <Card>
                <div className="bg-gray-900 rounded-md p-4 text-xs font-mono text-green-400 overflow-x-auto">
                  <div className="text-gray-500"># .env.local</div>
                  <div>NEXT_PUBLIC_API_BASE=http://localhost:8000</div>
                </div>
              </Card>
            </div>
          )}

          {activeSection === 'system' && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Health Check</CardTitle>
                </CardHeader>
                <div className="space-y-3">
                  {[
                    { name: 'Portal', status: 'Operational', color: 'text-green-600' },
                    { name: 'Mock API', status: 'Operational', color: 'text-green-600' },
                    { name: 'Database', status: 'Not connected (mock mode)', color: 'text-amber-600' },
                  ].map((item) => (
                    <div key={item.name} className="flex items-center gap-3">
                      <span className={`text-lg ${item.color}`}>●</span>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{item.name}</p>
                        <p className="text-xs text-gray-600">{item.status}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="bg-gray-50">
                <div className="text-xs font-mono text-gray-700 space-y-2">
                  <div>
                    <span className="text-gray-600">Portal Version:</span>{' '}
                    <span className="font-semibold">0.1.0</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Next.js:</span>{' '}
                    <span className="font-semibold">14.2.x</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Node.js:</span>{' '}
                    <span className="font-semibold">{process.version}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Build:</span>{' '}
                    <span className="font-semibold">Development</span>
                  </div>
                </div>
              </Card>

              <Card className="bg-blue-50 border-blue-200">
                <p className="text-sm text-blue-800">
                  <span className="font-semibold">Satellite Data Integration:</span> Live satellite ingestion
                  requires FastAPI backend + Sentinel-2 credentials. Contact system administrator.
                </p>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

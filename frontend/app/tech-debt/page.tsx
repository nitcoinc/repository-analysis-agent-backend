'use client'

import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import DebtVisualization from '@/components/tech-debt/DebtVisualization'
import DebtList from '@/components/tech-debt/DebtList'
import RemediationPlan from '@/components/tech-debt/RemediationPlan'

export default function TechDebtPage() {
  const [repositoryId, setRepositoryId] = useState('')
  const [selectedTab, setSelectedTab] = useState<'overview' | 'items' | 'plan'>('overview')

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['tech-debt-metrics', repositoryId],
    queryFn: async () => {
      if (!repositoryId) return null
      const response = await api.get(`/api/tech-debt/metrics/${repositoryId}`)
      return response.data
    },
    enabled: !!repositoryId,
  })

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['tech-debt-report', repositoryId],
    queryFn: async () => {
      if (!repositoryId) return null
      const response = await api.get(`/api/tech-debt/reports/${repositoryId}`)
      return response.data
    },
    enabled: !!repositoryId,
  })

  const { mutate: runAnalysis, isPending: analysisPending } = useMutation({
    mutationFn: async (repoId: string) => {
      const response = await api.post('/api/tech-debt/analyze', {
        repository_id: repoId,
      })
      return response.data
    },
  })

  const handleAnalyze = () => {
    if (repositoryId) {
      runAnalysis(repositoryId)
    }
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Technical Debt Analysis</h1>

        {/* Repository Selection */}
        <div className="mb-6 p-4 border rounded-lg">
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-2">
                Repository ID
              </label>
              <input
                type="text"
                value={repositoryId}
                onChange={(e) => setRepositoryId(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="Enter repository ID"
              />
            </div>
            <Button onClick={handleAnalyze} disabled={analysisPending || !repositoryId}>
              {analysisPending ? 'Analyzing...' : 'Run Analysis'}
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6 border-b">
          <div className="flex gap-4">
            <button
              onClick={() => setSelectedTab('overview')}
              className={`px-4 py-2 border-b-2 ${
                selectedTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setSelectedTab('items')}
              className={`px-4 py-2 border-b-2 ${
                selectedTab === 'items'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600'
              }`}
            >
              Debt Items
            </button>
            <button
              onClick={() => setSelectedTab('plan')}
              className={`px-4 py-2 border-b-2 ${
                selectedTab === 'plan'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600'
              }`}
            >
              Remediation Plan
            </button>
          </div>
        </div>

        {/* Content */}
        {metricsLoading || reportLoading ? (
          <div className="text-center py-12">Loading...</div>
        ) : report ? (
          <>
            {selectedTab === 'overview' && (
              <div className="space-y-6">
                <DebtVisualization metrics={metrics} report={report} />
                
                {/* Top Priority Items */}
                <div className="p-6 border rounded-lg">
                  <h2 className="text-xl font-semibold mb-4">Top Priority Items</h2>
                  <div className="space-y-2">
                    {report.debt_items?.slice(0, 5).map((item: any) => (
                      <div key={item.id} className="p-3 border rounded">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{item.title}</p>
                            <p className="text-sm text-gray-600">{item.description}</p>
                          </div>
                          <div className="text-right">
                            <span className={`px-2 py-1 rounded text-xs ${
                              item.severity === 'critical' ? 'bg-red-100 text-red-800' :
                              item.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                              item.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {item.severity}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {selectedTab === 'items' && (
              <DebtList repositoryId={repositoryId} />
            )}

            {selectedTab === 'plan' && (
              <RemediationPlan repositoryId={repositoryId} />
            )}
          </>
        ) : (
          <div className="text-center py-12 text-gray-500">
            {repositoryId
              ? 'No tech debt analysis found. Run analysis first.'
              : 'Enter a repository ID to view tech debt analysis.'}
          </div>
        )}
      </div>
    </div>
  )
}

'use client'

import { useQuery, useMutation } from '@tanstack/react-query'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'

interface RemediationPlanProps {
  repositoryId: string
}

export default function RemediationPlan({ repositoryId }: RemediationPlanProps) {
  const { data: plan, isLoading, refetch } = useQuery({
    queryKey: ['remediation-plan', repositoryId],
    queryFn: async () => {
      const response = await api.post('/api/tech-debt/remediation-plan', {
        repository_id: repositoryId,
      })
      return response.data
    },
    enabled: !!repositoryId,
  })

  const { mutate: generatePlan, isPending } = useMutation({
    mutationFn: async () => {
      const response = await api.post('/api/tech-debt/remediation-plan', {
        repository_id: repositoryId,
      })
      return response.data
    },
    onSuccess: () => {
      refetch()
    },
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (!plan) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 mb-4">No remediation plan found.</p>
        <Button onClick={() => generatePlan()} disabled={isPending}>
          {isPending ? 'Generating...' : 'Generate Remediation Plan'}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Plan Overview */}
      <div className="p-6 border rounded-lg">
        <h2 className="text-xl font-semibold mb-4">{plan.plan_name || 'Remediation Plan'}</h2>
        
        {plan.priority_breakdown && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="p-4 bg-green-50 rounded-lg">
              <p className="text-sm text-gray-600">Quick Wins</p>
              <p className="text-2xl font-bold text-green-700">
                {plan.priority_breakdown.quick_wins || 0}
              </p>
            </div>
            <div className="p-4 bg-yellow-50 rounded-lg">
              <p className="text-sm text-gray-600">Strategic</p>
              <p className="text-2xl font-bold text-yellow-700">
                {plan.priority_breakdown.strategic || 0}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">Fill-ins</p>
              <p className="text-2xl font-bold text-gray-700">
                {plan.priority_breakdown.fill_ins || 0}
              </p>
            </div>
          </div>
        )}

        {plan.total_estimated_effort && (
          <div className="mb-4">
            <p className="text-sm text-gray-600">Total Estimated Effort</p>
            <p className="text-lg font-semibold">{plan.total_estimated_effort}</p>
          </div>
        )}
      </div>

      {/* Sprint Allocation */}
      {plan.sprint_allocation && (
        <div className="p-6 border rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Sprint Allocation</h3>
          <div className="space-y-4">
            {Object.entries(plan.sprint_allocation).map(([sprint, allocation]: [string, any]) => (
              <div key={sprint} className="p-4 bg-gray-50 rounded-lg">
                <h4 className="font-semibold mb-2">{sprint.replace('_', ' ').toUpperCase()}</h4>
                <p className="text-sm text-gray-600 mb-2">
                  <span className="font-medium">Focus:</span> {allocation.focus}
                </p>
                <p className="text-sm text-gray-600 mb-2">
                  <span className="font-medium">Estimated Effort:</span> {allocation.estimated_effort}
                </p>
                {allocation.items && allocation.items.length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm font-medium mb-2">Items ({allocation.items.length}):</p>
                    <ul className="list-disc list-inside space-y-1">
                      {allocation.items.slice(0, 5).map((item: any, idx: number) => (
                        <li key={idx} className="text-sm text-gray-700">
                          {item.title || item.id}
                        </li>
                      ))}
                      {allocation.items.length > 5 && (
                        <li className="text-sm text-gray-500">
                          ... and {allocation.items.length - 5} more
                        </li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {plan.recommendations && plan.recommendations.length > 0 && (
        <div className="p-6 border rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Top Recommendations</h3>
          <ul className="space-y-2">
            {plan.recommendations.map((rec: string, idx: number) => (
              <li key={idx} className="flex items-start">
                <span className="mr-2 text-blue-600">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ROI Analysis */}
      {plan.roi_analysis && (
        <div className="p-6 border rounded-lg">
          <h3 className="text-lg font-semibold mb-4">ROI Analysis</h3>
          <div className="space-y-2">
            {Object.entries(plan.roi_analysis).map(([key, value]: [string, any]) => (
              <div key={key} className="flex justify-between">
                <span className="text-sm text-gray-600">
                  {key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                </span>
                <span className="text-sm font-medium">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <Button onClick={() => generatePlan()} disabled={isPending}>
          {isPending ? 'Regenerating...' : 'Regenerate Plan'}
        </Button>
      </div>
    </div>
  )
}

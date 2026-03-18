'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

interface DebtListProps {
  repositoryId: string
}

export default function DebtList({ repositoryId }: DebtListProps) {
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [priorityFilter, setPriorityFilter] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['tech-debt-items', repositoryId, categoryFilter, severityFilter, priorityFilter],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (repositoryId) params.append('repository_id', repositoryId)
      if (categoryFilter) params.append('category', categoryFilter)
      if (severityFilter) params.append('severity', severityFilter)
      if (priorityFilter) params.append('priority', priorityFilter.toString())

      const response = await api.get(`/api/tech-debt/items?${params.toString()}`)
      return response.data
    },
    enabled: !!repositoryId,
  })

  const items = data?.items || []

  const categories = Array.from(new Set(items.map((item: any) => item.category)))
  const severities = ['critical', 'high', 'medium', 'low']

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="p-4 border rounded-lg bg-gray-50">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Category</label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full p-2 border rounded"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Severity</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="w-full p-2 border rounded"
            >
              <option value="">All Severities</option>
              {severities.map((sev) => (
                <option key={sev} value={sev}>
                  {sev.charAt(0).toUpperCase() + sev.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Priority</label>
            <select
              value={priorityFilter || ''}
              onChange={(e) => setPriorityFilter(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full p-2 border rounded"
            >
              <option value="">All Priorities</option>
              <option value="1">Priority 1 (Quick Wins)</option>
              <option value="2">Priority 2 (Strategic)</option>
              <option value="3">Priority 3 (Fill-ins)</option>
              <option value="4">Priority 4 (Avoid)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Items List */}
      <div className="space-y-3">
        {items.length > 0 ? (
          items.map((item: any) => (
            <div key={item.id} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg">{item.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                  {item.file_path && (
                    <p className="text-xs text-gray-500 mt-2">
                      {item.file_path}
                      {item.line_start && ` (lines ${item.line_start}-${item.line_end || item.line_start})`}
                    </p>
                  )}
                </div>
                <div className="flex gap-2 ml-4">
                  <span
                    className={`px-2 py-1 rounded text-xs font-semibold ${
                      item.severity === 'critical'
                        ? 'bg-red-100 text-red-800'
                        : item.severity === 'high'
                        ? 'bg-orange-100 text-orange-800'
                        : item.severity === 'medium'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {item.severity}
                  </span>
                  {item.priority && (
                    <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-800">
                      P{item.priority}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex gap-4 mt-3 text-sm">
                <span className="text-gray-600">
                  Category: <span className="font-medium">{item.category}</span>
                </span>
                <span className="text-gray-600">
                  Impact: <span className="font-medium">{(item.impact_score * 100).toFixed(0)}%</span>
                </span>
                <span className="text-gray-600">
                  Effort: <span className="font-medium">{item.effort_estimate || 'Unknown'}</span>
                </span>
                <span className="text-gray-600">
                  Status: <span className="font-medium">{item.status || 'open'}</span>
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-12 text-gray-500">
            No debt items found matching the filters.
          </div>
        )}
      </div>

      {/* Summary */}
      {items.length > 0 && (
        <div className="p-4 border rounded-lg bg-gray-50">
          <p className="text-sm text-gray-600">
            Showing <span className="font-semibold">{items.length}</span> debt item(s)
          </p>
        </div>
      )}
    </div>
  )
}

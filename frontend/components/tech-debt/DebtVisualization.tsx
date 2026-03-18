'use client'

import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts'

interface DebtVisualizationProps {
  metrics: any
  report: any
}

const COLORS = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#f59e0b',
  low: '#84cc16',
}

export default function DebtVisualization({ metrics, report }: DebtVisualizationProps) {
  // Debt score gauge data
  const debtScore = metrics?.total_debt_score || 0
  const scoreColor = debtScore > 75 ? COLORS.critical : debtScore > 50 ? COLORS.high : debtScore > 25 ? COLORS.medium : COLORS.low

  // Category distribution
  const categoryData = metrics?.items_by_category
    ? Object.entries(metrics.items_by_category).map(([name, value]) => ({
        name: name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
        value,
      }))
    : []

  // Severity distribution
  const severityData = metrics?.items_by_severity
    ? Object.entries(metrics.items_by_severity).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
        fill: COLORS[name as keyof typeof COLORS] || COLORS.low,
      }))
    : []

  // Category scores
  const categoryScores = metrics?.category_scores
    ? Object.entries(metrics.category_scores).map(([name, value]) => ({
        name: name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
        score: value,
      }))
    : []

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Debt Score Gauge */}
      <div className="p-6 border rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Overall Debt Score</h3>
        <div className="text-center">
          <div className="relative inline-block">
            <div
              className="text-6xl font-bold"
              style={{ color: scoreColor }}
            >
              {debtScore.toFixed(1)}
            </div>
            <div className="text-sm text-gray-600 mt-2">out of 100</div>
          </div>
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="h-4 rounded-full transition-all"
                style={{
                  width: `${debtScore}%`,
                  backgroundColor: scoreColor,
                }}
              />
            </div>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            {debtScore > 75
              ? 'Critical debt level - Immediate action required'
              : debtScore > 50
              ? 'High debt level - Plan remediation'
              : debtScore > 25
              ? 'Moderate debt level - Monitor closely'
              : 'Low debt level - Good health'}
          </p>
        </div>
      </div>

      {/* Category Distribution */}
      <div className="p-6 border rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Debt by Category</h3>
        {categoryData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={categoryData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {categoryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={Object.values(COLORS)[index % 4]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center py-8 text-gray-500">No data available</div>
        )}
      </div>

      {/* Severity Distribution */}
      <div className="p-6 border rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Debt by Severity</h3>
        {severityData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={severityData}>
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center py-8 text-gray-500">No data available</div>
        )}
      </div>

      {/* Category Scores */}
      <div className="p-6 border rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Category Scores</h3>
        {categoryScores.length > 0 ? (
          <div className="space-y-3">
            {categoryScores.map((item) => (
              <div key={item.name}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">{item.name}</span>
                  <span className="text-sm font-semibold">{item.score.toFixed(1)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="h-2 rounded-full"
                    style={{
                      width: `${item.score}%`,
                      backgroundColor:
                        item.score > 75
                          ? COLORS.critical
                          : item.score > 50
                          ? COLORS.high
                          : item.score > 25
                          ? COLORS.medium
                          : COLORS.low,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">No data available</div>
        )}
      </div>
    </div>
  )
}

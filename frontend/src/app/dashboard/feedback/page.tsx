"use client";

import { ThumbsUp, ThumbsDown, TrendingUp, MessageSquare, Star, BarChart3 } from "lucide-react";

const feedbackStats = {
  totalFeedback: 2847,
  positive: 2341,
  negative: 506,
  avgRating: 4.2,
};

const recentFeedback = [
  { query: "What is the PTO policy?", rating: 5, comment: "Accurate and helpful!", dept: "HR", time: "10 min ago" },
  { query: "Contract renewal process", rating: 4, comment: "Good but could be more detailed", dept: "Legal", time: "25 min ago" },
  { query: "Q4 budget allocation", rating: 2, comment: "Answer was incomplete", dept: "Finance", time: "1 hour ago" },
  { query: "HIPAA compliance checklist", rating: 5, comment: "Perfect response", dept: "Clinical", time: "2 hours ago" },
];

export default function FeedbackAnalyticsPage() {
  const positiveRate = ((feedbackStats.positive / feedbackStats.totalFeedback) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <ThumbsUp className="h-8 w-8 text-green-500" />
          Feedback Analytics
        </h1>
        <p className="text-muted-foreground mt-1">
          User feedback and query quality metrics
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <MessageSquare className="h-8 w-8 text-blue-500" />
            <div>
              <p className="text-2xl font-bold">{feedbackStats.totalFeedback.toLocaleString()}</p>
              <p className="text-sm text-muted-foreground">Total Feedback</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <ThumbsUp className="h-8 w-8 text-green-500" />
            <div>
              <p className="text-2xl font-bold">{positiveRate}%</p>
              <p className="text-sm text-muted-foreground">Positive Rate</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <Star className="h-8 w-8 text-yellow-500" />
            <div>
              <p className="text-2xl font-bold">{feedbackStats.avgRating}</p>
              <p className="text-sm text-muted-foreground">Avg Rating</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <TrendingUp className="h-8 w-8 text-purple-500" />
            <div>
              <p className="text-2xl font-bold text-green-500">+12%</p>
              <p className="text-sm text-muted-foreground">This Week</p>
            </div>
          </div>
        </div>
      </div>

      {/* Feedback by Department */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Feedback by Department
          </h2>
          <div className="space-y-4">
            {[
              { dept: "HR", positive: 92, total: 456 },
              { dept: "Legal", positive: 88, total: 234 },
              { dept: "Finance", positive: 85, total: 567 },
              { dept: "Clinical", positive: 94, total: 345 },
              { dept: "Operations", positive: 79, total: 189 },
            ].map((item) => (
              <div key={item.dept}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{item.dept}</span>
                  <span className="text-sm text-muted-foreground">{item.positive}% positive</span>
                </div>
                <div className="w-full h-2 bg-muted rounded-full">
                  <div 
                    className="h-full bg-green-500 rounded-full" 
                    style={{ width: `${item.positive}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="font-semibold mb-4">Recent Feedback</h2>
          <div className="space-y-3">
            {recentFeedback.map((fb, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-muted/50">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium truncate flex-1">{fb.query}</span>
                  <div className="flex items-center gap-1 ml-2">
                    {fb.rating >= 4 ? (
                      <ThumbsUp className="h-4 w-4 text-green-500" />
                    ) : (
                      <ThumbsDown className="h-4 w-4 text-red-500" />
                    )}
                    <span className="text-sm">{fb.rating}/5</span>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mt-1">{fb.comment}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary">{fb.dept}</span>
                  <span className="text-xs text-muted-foreground">{fb.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

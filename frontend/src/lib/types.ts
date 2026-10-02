/** Shared API types mirroring the backend response shapes. */

export interface User {
  id: number
  name: string
  email: string
  role: 'USER' | 'ADMIN'
  is_active?: boolean
  created_at?: string
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  limit: number
  pages: number
  unread?: number
}

export interface LostItem {
  id: number
  name: string
  description: string
  category: string
  location: string
  latitude: number | null
  longitude: number | null
  images: string[] | null
  status: string
  user_id: number
  user_name?: string
  created_at?: string
}

export interface FoundItem extends LostItem {}

export interface Donation {
  id: number
  name: string
  description: string
  category: string
  condition: string
  location: string
  latitude: number | null
  longitude: number | null
  images: string[] | null
  status: string
  user_id: number
  user_name?: string
  created_at?: string
}

export interface Claim {
  id: number
  item_type: 'FOUND_ITEM' | 'LOST_ITEM' | 'DONATION'
  item_id: number
  claimant_id: number
  claimant?: User
  message: string | null
  verification_answers: Record<string, string> | null
  review_note: string | null
  status: string
  unread_messages?: number
  created_at?: string
}

export interface MatchExplanation {
  reasons: string[]
  confidence: string
  confidence_note: string
}

export interface Match {
  id: number
  lost_item_id: number
  found_item_id: number
  lost_item?: LostItem
  found_item?: FoundItem
  text_score: number
  image_score: number
  location_score: number
  category_score: number
  combined_score: number
  status: string
  explanation: MatchExplanation | null
  unread_messages?: number
  created_at?: string
}

export interface Message {
  id: number
  match_id: number | null
  claim_id: number | null
  sender_id: number
  sender_name: string | null
  body: string
  is_read: boolean
  created_at?: string
}

export interface Notification {
  id: number
  type: string
  title: string
  message: string | null
  related_type: string | null
  related_id: number | null
  is_read: boolean
  created_at?: string
}

export interface Report {
  id: number
  reporter_id: number
  target_type: string
  target_id: number
  reason: string
  description: string | null
  status: string
  created_at?: string
}

export interface Stats {
  users: number
  lost_items: number
  lost_active: number
  lost_resolved: number
  found_items: number
  found_active: number
  found_returned: number
  donations: number
  donations_available: number
}

export const CATEGORIES = [
  'Electronics', 'Wallet', 'Bag', 'Keys', 'Documents', 'Jewelry',
  'Clothing', 'Watch', 'Phone', 'Laptop', 'Tablet', 'Books', 'Accessories', 'Other',
] as const

export const CONDITIONS = ['NEW', 'LIKE_NEW', 'GOOD', 'FAIR'] as const

export const REPORT_REASONS = [
  'SCAM', 'INAPPROPRIATE_CONTENT', 'MISLEADING_INFORMATION',
  'DUPLICATE_LISTING', 'SUSPICIOUS_BEHAVIOR', 'OTHER',
] as const

export function statusColor(status: string): string {
  switch (status) {
    case 'ACTIVE':
    case 'AVAILABLE':
      return 'bg-emerald-100 text-emerald-700'
    case 'MATCHED':
    case 'RESERVED':
      return 'bg-amber-100 text-amber-700'
    case 'CLAIMED':
      return 'bg-sky-100 text-sky-700'
    case 'RESOLVED':
    case 'RETURNED':
      return 'bg-indigo-100 text-indigo-700'
    case 'CANCELLED':
      return 'bg-slate-200 text-slate-600'
    default:
      return 'bg-slate-100 text-slate-600'
  }
}

export function claimColor(status: string): string {
  switch (status) {
    case 'PENDING':
      return 'bg-amber-100 text-amber-700'
    case 'APPROVED':
      return 'bg-emerald-100 text-emerald-700'
    case 'REJECTED':
      return 'bg-rose-100 text-rose-700'
    default:
      return 'bg-slate-100 text-slate-600'
  }
}

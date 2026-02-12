/**
 * Reusable skeleton loading placeholders.
 * Uses the global `.skeleton` class from index.css for the shimmer animation.
 */

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ width = '100%', height = 16, borderRadius, style }: SkeletonProps) {
  return (
    <div
      className="skeleton"
      style={{
        width,
        height,
        borderRadius,
        ...style,
      }}
    />
  );
}

/** Page-level skeleton: simulates a typical dashboard/list page loading. */
export function PageSkeleton() {
  return (
    <div style={{ padding: '0', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Skeleton width="40%" height={28} />
      <Skeleton width="60%" height={16} />
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    </div>
  );
}

/** Card skeleton: simulates a course/task card. */
export function CardSkeleton() {
  return (
    <div
      style={{
        flex: '1 1 260px',
        maxWidth: 360,
        padding: 20,
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <Skeleton width="70%" height={18} />
      <Skeleton width="40%" height={14} />
      <Skeleton width="100%" height={14} />
    </div>
  );
}

/** List skeleton: simulates a list of rows (tasks, messages, etc.). */
export function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <Skeleton width={36} height={36} borderRadius="50%" />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <Skeleton width={`${60 + (i % 3) * 15}%`} height={14} />
            <Skeleton width={`${30 + (i % 2) * 20}%`} height={12} />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Detail page skeleton: simulates a detail page with header + content. */
export function DetailSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Skeleton width="50%" height={28} />
      <Skeleton width="30%" height={16} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
        <Skeleton width="100%" height={14} />
        <Skeleton width="100%" height={14} />
        <Skeleton width="85%" height={14} />
        <Skeleton width="92%" height={14} />
        <Skeleton width="70%" height={14} />
      </div>
    </div>
  );
}

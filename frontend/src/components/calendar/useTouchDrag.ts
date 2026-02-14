import { useRef, useCallback } from 'react';

interface DragData {
  id: number;
  itemType: string;
}

/**
 * Hook that adds touch-based drag-and-drop alongside native HTML5 drag-and-drop.
 * Returns handlers for drag source (entries) and drop targets (day cells / week columns).
 */
export function useTouchDrag(onTaskDrop?: (taskId: number, newDate: Date) => void) {
  const dragDataRef = useRef<DragData | null>(null);
  const dragGhostRef = useRef<HTMLDivElement | null>(null);
  const activeDropZoneRef = useRef<HTMLElement | null>(null);

  // --- Source handlers (CalendarEntry) ---

  const handleTouchStart = useCallback((e: React.TouchEvent, data: DragData) => {
    // Long-press is not needed — initiate immediately on tasks
    dragDataRef.current = data;
    const touch = e.touches[0];

    // Create visual ghost element
    const ghost = document.createElement('div');
    ghost.className = 'cal-touch-ghost';
    ghost.textContent = (e.currentTarget as HTMLElement).textContent?.slice(0, 30) || 'Task';
    ghost.style.position = 'fixed';
    ghost.style.left = `${touch.clientX - 40}px`;
    ghost.style.top = `${touch.clientY - 20}px`;
    ghost.style.pointerEvents = 'none';
    document.body.appendChild(ghost);
    dragGhostRef.current = ghost;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!dragDataRef.current) return;
    e.preventDefault(); // Prevent scroll while dragging

    const touch = e.touches[0];

    // Move ghost
    if (dragGhostRef.current) {
      dragGhostRef.current.style.left = `${touch.clientX - 40}px`;
      dragGhostRef.current.style.top = `${touch.clientY - 20}px`;
    }

    // Find drop zone under finger
    const elementUnder = document.elementFromPoint(touch.clientX, touch.clientY);
    const dropZone = elementUnder?.closest('[data-drop-date]') as HTMLElement | null;

    // Clear previous highlight
    if (activeDropZoneRef.current && activeDropZoneRef.current !== dropZone) {
      activeDropZoneRef.current.classList.remove('cal-day-drag-over');
    }

    // Highlight new drop zone
    if (dropZone) {
      dropZone.classList.add('cal-day-drag-over');
      activeDropZoneRef.current = dropZone;
    } else {
      activeDropZoneRef.current = null;
    }
  }, []);

  const handleTouchEnd = useCallback(() => {
    // Clean up ghost
    if (dragGhostRef.current) {
      dragGhostRef.current.remove();
      dragGhostRef.current = null;
    }

    // Clear highlight
    if (activeDropZoneRef.current) {
      activeDropZoneRef.current.classList.remove('cal-day-drag-over');
    }

    // Execute drop
    if (dragDataRef.current && activeDropZoneRef.current && onTaskDrop) {
      const dateStr = activeDropZoneRef.current.getAttribute('data-drop-date');
      if (dateStr) {
        const [y, m, d] = dateStr.split('-').map(Number);
        const newDate = new Date(y, m - 1, d);
        onTaskDrop(dragDataRef.current.id, newDate);
      }
    }

    dragDataRef.current = null;
    activeDropZoneRef.current = null;
  }, [onTaskDrop]);

  return { handleTouchStart, handleTouchMove, handleTouchEnd };
}

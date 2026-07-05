export type TimeSortable = {
  start_time: string | null;
};

/**
 * Sort an array of objects by start_time ascending.
 * Items without start_time are placed at the end.
 */
export function sortByTime<T extends TimeSortable>(arr: T[]): T[] {
  return [...arr].sort((a, b) => {
    if (!a.start_time && !b.start_time) return 0;
    if (!a.start_time) return 1;
    if (!b.start_time) return -1;
    return a.start_time.localeCompare(b.start_time);
  });
}

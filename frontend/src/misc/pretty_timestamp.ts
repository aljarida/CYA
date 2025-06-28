export default function pretty_timestamp(t: string) {
  const cleanedTimestamp = t.slice(0, 23) + 'Z';
  const date = new Date(cleanedTimestamp);
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

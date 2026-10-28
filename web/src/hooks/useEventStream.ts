import { useState, useEffect, useRef } from 'react';
import { API_BASE_URL, SeismicEvent } from '../api/client';
import { useAuth } from '../context/AuthContext';

export function useEventStream(onNewEvents?: (events: SeismicEvent[]) => void) {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastHeartbeat, setLastHeartbeat] = useState<string | null>(null);
  const [liveEvents, setLiveEvents] = useState<SeismicEvent[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const { token } = useAuth();

  useEffect(() => {
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    const connectSSE = () => {
      const streamUrl = `${API_BASE_URL}/api/stream${token ? `?token=${encodeURIComponent(token)}` : ''}`;
      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
      };

      es.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'connected' || payload.type === 'heartbeat') {
            setIsConnected(true);
            setLastHeartbeat(payload.timestamp || new Date().toISOString());
          } else if (payload.type === 'new_events') {
            const incoming: SeismicEvent[] = payload.events || [];
            if (incoming.length > 0) {
              setLiveEvents((prev) => {
                const existingIds = new Set(prev.map((e) => e.event_id));
                const fresh = incoming.filter((e) => !existingIds.has(e.event_id));
                return [...fresh, ...prev].slice(0, 50);
              });

              if (onNewEvents) {
                onNewEvents(incoming);
              }
            }
          }
        } catch (err) {
          console.warn('Error parseando mensaje SSE:', err);
        }
      };

      es.onerror = () => {
        setIsConnected(false);
        es.close();
        // Intentar reconectar tras 4 segundos
        reconnectTimeout = setTimeout(connectSSE, 4000);
      };
    };

    connectSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      clearTimeout(reconnectTimeout);
    };
  }, [token]);

  return {
    isConnected,
    lastHeartbeat,
    liveEvents,
  };
}

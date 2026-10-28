import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { SeismicEvent } from '../api/client';

interface SeismicMapProps {
  events: SeismicEvent[];
  selectedEventId?: string | null;
  onSelectEvent?: (event: SeismicEvent) => void;
}

export const SeismicMap: React.FC<SeismicMapProps> = ({ events, selectedEventId, onSelectEvent }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      // Inicializar mapa centrado globalmente
      const map = L.map(mapContainerRef.current, {
        center: [15, 0],
        zoom: 2,
        minZoom: 1.5,
        maxZoom: 12,
        worldCopyJump: true,
      });

      // Capa base OpenStreetMap oficial (100% gratuita, sin API keys ni restricciones)
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        className: 'dark-galactic-tiles',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      const markersGroup = L.layerGroup().addTo(map);
      markersLayerRef.current = markersGroup;
      mapInstanceRef.current = map;
    }

    return () => {
      // Cleanup al desmontar si es necesario
    };
  }, []);

  // Actualizar marcadores cuando cambian los eventos
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();

    events.forEach((ev) => {
      if (ev.latitude == null || ev.longitude == null) return;

      const mag = ev.mag ?? 0;
      let color = '#38bdf8'; // Cyan (< 4.5)
      let radius = 6;

      if (mag >= 6.0) {
        color = '#ef4444'; // Crimson (>= 6.0)
        radius = 12;
      } else if (mag >= 4.5) {
        color = '#f59e0b'; // Amber (4.5 - 5.9)
        radius = 9;
      }

      const isSelected = ev.event_id === selectedEventId;
      if (isSelected) {
        radius += 4;
      }

      const marker = L.circleMarker([ev.latitude, ev.longitude], {
        radius,
        fillColor: color,
        color: isSelected ? '#ffffff' : color,
        weight: isSelected ? 3 : 1.5,
        opacity: 0.9,
        fillOpacity: 0.7,
      });

      const popupContent = `
        <div style="font-size: 13px; line-height: 1.4;">
          <div style="font-weight: 700; color: ${color}; font-size: 14px; margin-bottom: 4px;">
            Magnitud ${mag.toFixed(1)} ${ev.mag_type ? `(${ev.mag_type})` : ''}
          </div>
          <div style="color: #f8fafc; margin-bottom: 6px;">${ev.place || 'Ubicación no especificada'}</div>
          <div style="font-size: 11px; color: #94a3b8;">
            <strong>Profundidad:</strong> ${ev.depth_km?.toFixed(1) || '0'} km<br/>
            <strong>Fecha UTC:</strong> ${new Date(ev.time_utc).toUTCString()}<br/>
            <strong>Tsunami:</strong> ${ev.tsunami > 0 ? '⚠️ Alerta Emitida' : 'No reportada'}
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on('click', () => {
        if (onSelectEvent) {
          onSelectEvent(ev);
        }
      });

      markersLayerRef.current?.addLayer(marker);
    });
  }, [events, selectedEventId, onSelectEvent]);

  return (
    <div className="glass-panel" style={{ padding: '16px', position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h3 style={{ fontSize: '15px', color: '#f8fafc' }}>
          Mapa Sísmico Global en Tiempo Casi Real
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '11px', color: 'var(--text-muted)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#38bdf8' }} /> &lt; 4.5 Ligero
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} /> 4.5 - 5.9 Moderado
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444' }} /> &ge; 6.0 Mayor
          </span>
        </div>
      </div>
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '420px',
          borderRadius: 'var(--radius-sm)',
          overflow: 'hidden',
          zIndex: 1,
        }}
      />
    </div>
  );
};

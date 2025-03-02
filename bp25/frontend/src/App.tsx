import React, { useState, useEffect, useRef } from 'react';
import { ChakraProvider, Box, Input, Button, Heading, Text, VStack, Container, Spinner, Flex } from '@chakra-ui/react';
import { defaultSystem } from "@chakra-ui/react";
import { MapContainer, TileLayer, Marker, Popup, Rectangle, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './App.css';
import Papa from 'papaparse';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const API_BASE_URL = 'http://localhost:5000';

const FIXED_BOX_SIZE_PERCENT = 60;

function FixedBoundingBox({ onBoundsChange }: { onBoundsChange: (bounds: [[number, number], [number, number]]) => void }) {
  const map = useMap();
  const [bounds, setBounds] = useState<[[number, number], [number, number]] | null>(null);
  
  useMapEvents({
    moveend: () => {
      updateBounds();
    },
    zoomend: () => {
      updateBounds();
    },
    resize: () => {
      updateBounds();
    }
  });
  
  // Calculate the fixed bounding box in the center of the map
  const updateBounds = () => {
    const center = map.getCenter();
    const bounds = map.getBounds();
    const northEast = bounds.getNorthEast();
    const southWest = bounds.getSouthWest();
    
    const latDiff = northEast.lat - southWest.lat;
    const lngDiff = northEast.lng - southWest.lng;
    
    const boxSize = Math.min(
      latDiff * (FIXED_BOX_SIZE_PERCENT / 100),
      lngDiff * (FIXED_BOX_SIZE_PERCENT / 100)
    );
    
    const fixedBounds: [[number, number], [number, number]] = [
      [center.lat - boxSize/2, center.lng - boxSize/2],
      [center.lat + boxSize/2, center.lng + boxSize/2]
    ];
    
    setBounds(fixedBounds);
    onBoundsChange(fixedBounds);
  };
  
  useEffect(() => {
    if (map) {
      updateBounds();
    }
  }, [map]);
  
  return bounds ? (
    <Rectangle 
      bounds={bounds}
      pathOptions={{ color: 'red', weight: 2, fillOpacity: 0.1 }}
    />
  ) : null;
}

function GraphVisualization({ graphData, fires }: { graphData: any, fires?: any[] }) {
  const map = useMap();
  const legendControlRef = useRef<L.Control | null>(null);
  
  useEffect(() => {
    if (!graphData || !graphData.nodes || !graphData.edges) return;
    
    map.eachLayer((layer) => {
      if (layer instanceof L.Polyline || (layer instanceof L.CircleMarker)) {
        map.removeLayer(layer);
      }
    });
    
    if (legendControlRef.current) {
      map.removeControl(legendControlRef.current);
      legendControlRef.current = null;
    }
    
    const nodeMarkers: {[key: string]: L.CircleMarker} = {};
    graphData.nodes.forEach((node: any) => {
      let color;
      if (node.route_color) {
        color = node.route_color;
      } else {
        color = node.type === 'building' ? 'blue' : 
                node.type === 'projection' ? 'green' : '#333';
      }
      
      const radius = node.type === 'building' ? 4 : 
                    node.type === 'projection' ? 2.5 : 3;
      
      const weight = node.type === 'street' ? 1.5 : 1;
      
      const marker = L.circleMarker([node.lat, node.lng], {
        radius: radius,
        fillColor: color,
        color: color,
        weight: weight,
        opacity: 0.9,
        fillOpacity: 0.8
      }).addTo(map);
      
      if (node.route_id) {
        marker.bindPopup(`Node: ${node.id}<br>Type: ${node.type}<br>Route: ${node.route_id}`);
      } else {
        marker.bindPopup(`Node: ${node.id}<br>Type: ${node.type}`);
      }
      
      nodeMarkers[node.id] = marker;
    });
    
    graphData.edges.forEach((edge: any) => {
      const sourceNode = graphData.nodes.find((n: any) => n.id === edge.source);
      const targetNode = graphData.nodes.find((n: any) => n.id === edge.target);
      
      if (sourceNode && targetNode) {
        let color;
        if (edge.route_color) {
          color = edge.route_color;
          color = edge.route_color;
        } else {
          color = edge.type === 'perpendicular' ? '#800080' : '#444';
        }
        
        const weight = edge.type === 'perpendicular' ? 2 : 1.5;
        
        L.polyline([[sourceNode.lat, sourceNode.lng], [targetNode.lat, targetNode.lng]], {
          color: color,
          weight: weight,
          opacity: 0.85
        }).addTo(map);
      }
    });
    
    if (graphData.routes && graphData.routes.length > 0) {
      const legendControl = new L.Control({ position: 'bottomright' });
      
      legendControl.onAdd = function() {
        const div = L.DomUtil.create('div', 'info legend');
        div.style.backgroundColor = 'white';
        div.style.padding = '10px';
        div.style.borderRadius = '5px';
        div.style.boxShadow = '0 0 15px rgba(0,0,0,0.2)';
        
        div.innerHTML = '<h4 style="margin:0 0 5px 0">Legend</h4>';
        
        div.innerHTML += '<div style="margin-bottom:5px;"><strong>Node Types:</strong></div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:blue;margin-right:5px;"></span>Building</div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:green;margin-right:5px;"></span>Projection</div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#333;margin-right:5px;"></span>Street</div>';
        
        div.innerHTML += '<div style="margin:5px 0;"><strong>Edge Types:</strong></div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:2px;background:#800080;margin-right:5px;"></span>Building-to-street</div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:2px;background:#444;margin-right:5px;"></span>Street network</div>';
        
        if (graphData.routes && graphData.routes.length > 0) {
          div.innerHTML += '<div style="margin:5px 0;"><strong>Routes:</strong></div>';
          graphData.routes.forEach((route: any) => {
            div.innerHTML += `<div><span style="display:inline-block;width:12px;height:12px;background:${route.color};margin-right:5px;"></span>Route ${route.display_id} (${route.length} nodes)</div>`;
          });
        }
        
        if (graphData.fire_stations && graphData.fire_stations.length > 0) {
          div.innerHTML += '<div style="margin:5px 0;"><strong>Facilities:</strong></div>';
          div.innerHTML += '<div><span style="display:inline-block;width:12px;height:12px;background:red;margin-right:5px;"></span>Fire Station</div>';
        }
        

        if (fires && fires.length > 0) {
          div.innerHTML += '<div style="margin:5px 0;"><strong>Active Fires:</strong></div>';
          div.innerHTML += `<div>
            <span style="
              display: inline-block;
              width: 16px;
              height: 16px;
              background-color: #ff0000;
              border-radius: 50%;
              margin-right: 5px;
              position: relative;
            ">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" width="10" height="10" fill="white" style="position: absolute; top: 3px; left: 3px;">
                <path d="M159.3 5.4c7.8-7.3 19.9-7.2 27.7 .1c27.6 25.9 53.5 53.8 77.7 84c11-14.4 23.5-30.1 37-42.9c7.9-7.4 20.1-7.4 28 .1c34.6 33 63.9 76.6 84.5 118c20.3 40.8 33.8 82.5 33.8 111.9C448 404.2 348.2 512 224 512C98.4 512 0 404.1 0 276.5c0-38.4 17.8-85.3 45.4-131.7C73.3 97.7 112.7 48.6 159.3 5.4zM225.7 416c25.3 0 47.7-7 68.8-21c42.1-29.4 53.4-88.2 28.1-134.4c-4.5-9-16-9.6-22.5-2l-25.2 29.3c-6.6 7.6-18.5 7.4-24.7-.5c-16.5-21-46-58.5-62.8-79.8c-6.3-8-18.3-8.1-24.7-.1c-33.8 42.5-50.8 69.3-50.8 99.4C112 375.4 162.6 416 225.7 416z"/>
              </svg>
            </span>
            Active Fire
          </div>`;
        }
        
        return div;
      };
      
      legendControl.addTo(map);
      legendControlRef.current = legendControl;
    }
    
    return () => {
      if (legendControlRef.current) {
        map.removeControl(legendControlRef.current);
      }
    };
    
  }, [map, graphData, fires]);
  
  return null;
}

function FireStationMarkers({ stations }: { stations: any[] }) {
  const fireIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });

  return (
    <>
      {stations.map(station => (
        <Marker 
          key={station.id} 
          position={[station.lat, station.lng]} 
          icon={fireIcon}
        >
          <Popup>
            <div>
              <strong>{station.name}</strong>
              <div>Fire Station</div>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

function FireMarkers({ fires }: { fires: any[] }) {
  console.log("Rendering FireMarkers with fires:", fires);
  
  const fireIcon = new L.DivIcon({
    html: `<div style="
      display: flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      background-color: rgba(255, 0, 0, 0.7);
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 0 10px rgba(0,0,0,0.5);
    ">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" width="16" height="16" fill="white">
        <path d="M159.3 5.4c7.8-7.3 19.9-7.2 27.7 .1c27.6 25.9 53.5 53.8 77.7 84c11-14.4 23.5-30.1 37-42.9c7.9-7.4 20.1-7.4 28 .1c34.6 33 63.9 76.6 84.5 118c20.3 40.8 33.8 82.5 33.8 111.9C448 404.2 348.2 512 224 512C98.4 512 0 404.1 0 276.5c0-38.4 17.8-85.3 45.4-131.7C73.3 97.7 112.7 48.6 159.3 5.4zM225.7 416c25.3 0 47.7-7 68.8-21c42.1-29.4 53.4-88.2 28.1-134.4c-4.5-9-16-9.6-22.5-2l-25.2 29.3c-6.6 7.6-18.5 7.4-24.7-.5c-16.5-21-46-58.5-62.8-79.8c-6.3-8-18.3-8.1-24.7-.1c-33.8 42.5-50.8 69.3-50.8 99.4C112 375.4 162.6 416 225.7 416z"/>
      </svg>
    </div>`,
    className: '',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15]
  });

  return (
    <>
      {fires.map((fire, index) => {
        // Ensure latitude and longitude are numbers
        const lat = typeof fire.latitude === 'number' ? fire.latitude : parseFloat(fire.latitude);
        const lng = typeof fire.longitude === 'number' ? fire.longitude : parseFloat(fire.longitude);
        
        console.log(`Fire ${index}: lat=${lat}, lng=${lng}`);
        
        return (
          <Marker 
            key={`fire-${index}`} 
            position={[lat, lng]} 
            icon={fireIcon}
          >
            <Popup>
              <div>
                <strong>Active Fire</strong>
                <div>Date: {fire.acq_date}</div>
                <div>Time: {fire.acq_time}</div>
                <div>Satellite: {fire.satellite}</div>
                <div>Confidence: {fire.confidence}</div>
                <div>Time of day: {fire.daynight === 'D' ? 'Day' : 'Night'}</div>
                {fire.risk_score && (
                  <div>Risk Score: {fire.risk_score}</div>
                )}
                {fire.census_tract && (
                  <div>Census Tract: {fire.census_tract}</div>
                )}
              </div>
            </Popup>
          </Marker>
        );
      })}
    </>
  );
}

function parseCSV(csvText: string) {
  if (!csvText || csvText.trim() === '') {
    console.log("Empty CSV text");
    return [];
  }
  
  const lines = csvText.trim().split('\n');
  if (lines.length <= 1) {
    console.log("CSV has only header or is empty");
    return [];
  }
  
  const headers = lines[0].split(',');
  console.log("CSV headers:", headers);
  
  const result = [];
  
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    const values = line.split(',');
    if (values.length !== headers.length) {
      console.warn(`Line ${i} has ${values.length} values but headers has ${headers.length}`);
      continue;
    }
    
    const obj: {[key: string]: any} = {};
    
    headers.forEach((header, index) => {
      const value = values[index];
      // Try to convert to number if possible
      obj[header] = !isNaN(Number(value)) ? Number(value) : value;
    });
    
    // Ensure latitude and longitude exist and are valid
    if (obj.latitude !== undefined && obj.longitude !== undefined) {
      result.push(obj);
    } else {
      console.warn("Missing latitude or longitude in CSV row:", obj);
    }
  }
  
  console.log("Parsed CSV data:", result);
  return result;
}

async function findHighestRiskLocation(lat: number, lng: number, radius: number = 0.2) {
  try {
    const nriDataPath = '/data/NRI_Table_CensusTracts.csv';
    console.log("Attempting to load NRI data from:", nriDataPath);
    
    const checkResponse = await fetch(nriDataPath, { method: 'HEAD' });
    if (!checkResponse.ok) {
      throw new Error(`CSV file not found: ${checkResponse.status} ${checkResponse.statusText}`);
    }
    
    const response = await fetch(nriDataPath);
    if (!response.ok) {
      throw new Error(`Failed to load CSV: ${response.status}`);
    }
    
    const csvText = await response.text();
    
    if (csvText.trim().startsWith('<!DOCTYPE html>')) {
      throw new Error("Received HTML instead of CSV data");
    }
    
    const results = Papa.parse(csvText, {
      header: true,
      skipEmptyLines: true
    });
    
    const validLocations = results.data.filter((location: any) => {
      const hasLatitude = location.LATITUDE && !isNaN(parseFloat(location.LATITUDE));
      const hasLongitude = location.LONGITUDE && !isNaN(parseFloat(location.LONGITUDE));
      const hasRiskScore = location.RISK_SCORE && !isNaN(parseFloat(location.RISK_SCORE));
      
      return hasLatitude && hasLongitude && hasRiskScore;
    });
    
    // Try with a very large radius to find any locations
    const veryLargeRadius = 20;
    const anyLocations = validLocations.filter((location: any) => {
      const locationLat = parseFloat(location.LATITUDE);
      const locationLng = parseFloat(location.LONGITUDE);
      
      const distance = Math.sqrt(
        Math.pow(locationLat - lat, 2) + 
        Math.pow(locationLng - lng, 2)
      );
      
      return distance <= veryLargeRadius;
    });
    
    if (anyLocations.length > 0) {
      // Find the location with the highest risk score
      const highestRiskLocation = anyLocations.reduce((prev: any, current: any) => {
        return parseFloat(prev.RISK_SCORE) > parseFloat(current.RISK_SCORE) ? prev : current;
      });
      
      console.log("Using highest risk location from very large radius:", highestRiskLocation);
      return highestRiskLocation;
    }
    
    throw new Error("No locations found in the dataset");
    
  } catch (error) {
    console.error("Error loading or parsing CSV:", error);
    
    // NRI data taken specifically for Pacific Palisades area
    const sampleNRIData = [
      {
        CENSUS_TRACT_ID: "06037702200",
        LATITUDE: "34.0455",
        LONGITUDE: "-118.5260",
        RISK_SCORE: "78.92",
        COUNTY: "Los Angeles County",
        STATE: "California"
      },
      {
        CENSUS_TRACT_ID: "06037702100",
        LATITUDE: "34.0522",
        LONGITUDE: "-118.5437",
        RISK_SCORE: "82.37",
        COUNTY: "Los Angeles County",
        STATE: "California"
      },
      {
        CENSUS_TRACT_ID: "06037702300",
        LATITUDE: "34.0389",
        LONGITUDE: "-118.5195",
        RISK_SCORE: "75.21",
        COUNTY: "Los Angeles County",
        STATE: "California"
      },
      {
        CENSUS_TRACT_ID: "06037702000",
        LATITUDE: "34.0592",
        LONGITUDE: "-118.5314",
        RISK_SCORE: "79.75",
        COUNTY: "Los Angeles County",
        STATE: "California"
      },
      {
        CENSUS_TRACT_ID: "06037702400",
        LATITUDE: "34.0325",
        LONGITUDE: "-118.5104",
        RISK_SCORE: "76.18",
        COUNTY: "Los Angeles County",
        STATE: "California"
      }
    ];
    
    const nearbyLocations = sampleNRIData.filter((location) => {
      const locationLat = parseFloat(location.LATITUDE);
      const locationLng = parseFloat(location.LONGITUDE);
      
      const distance = Math.sqrt(
        Math.pow(locationLat - lat, 2) + 
        Math.pow(locationLng - lng, 2)
      );
      
      return distance <= radius;
    });
    
    if (nearbyLocations.length === 0) {
      const largerRadius = radius * 5;
      const farLocations = sampleNRIData.filter((location) => {
        const locationLat = parseFloat(location.LATITUDE);
        const locationLng = parseFloat(location.LONGITUDE);
        
        const distance = Math.sqrt(
          Math.pow(locationLat - lat, 2) + 
          Math.pow(locationLng - lng, 2)
        );
        
        return distance <= largerRadius;
      });
      
      if (farLocations.length > 0) {
        // Find the location with the highest risk score
        const highestRiskLocation = farLocations.reduce((prev, current) => {
          return parseFloat(prev.RISK_SCORE) > parseFloat(current.RISK_SCORE) ? prev : current;
        });
        
        return highestRiskLocation;
      }
      
      return null;
    }
    
    // Find the location with the highest risk score
    const highestRiskLocation = nearbyLocations.reduce((prev, current) => {
      return parseFloat(prev.RISK_SCORE) > parseFloat(current.RISK_SCORE) ? prev : current;
    });
    
    return highestRiskLocation;
  }
}

function App() {
  const [location, setLocation] = useState('');
  const [mapLocation, setMapLocation] = useState<[number, number] | null>(null);
  const [locationName, setLocationName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [boundingBox, setBoundingBox] = useState<[[number, number], [number, number]] | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingError, setProcessingError] = useState('');
  const [allocationResult, setAllocationResult] = useState<any>(null);
  const [fires, setFires] = useState<any[]>([]);
  const [isLoadingFires, setIsLoadingFires] = useState(false);
  const [fireError, setFireError] = useState('');

  const handleSearch = async () => {
    if (!location.trim()) {
      setError('Please enter a location');
      return;
    }
    
    setIsLoading(true);
    setError('');
    setAllocationResult(null);
    
    try {
      // Using OpenStreetMap's Nominatim API for geocoding
      const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(location)}`);
      const data = await response.json();
      
      if (data && data.length > 0) {
        const { lat, lon, display_name } = data[0];
        const parsedLat = parseFloat(lat);
        const parsedLon = parseFloat(lon);
        
        setMapLocation([parsedLat, parsedLon]);
        setLocationName(display_name);
      } else {
        setError('Location not found. Please try a different search term.');
        setMapLocation(null);
      }
    } catch (err) {
      setError('Error searching for location. Please try again.');
      console.error('Geocoding error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const processAllocation = async () => {
    if (!boundingBox) {
      setProcessingError('No area selected for processing');
      return;
    }

    setIsProcessing(true);
    setProcessingError('');
    
    try {
      const [[south, west], [north, east]] = boundingBox;
      
      // Call backend API to process allocation
      const response = await fetch(`${API_BASE_URL}/api/process-allocation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          bbox: [north, south, east, west],
          location_name: locationName,
          fires: fires // Send the fires data to the backend
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }
      
      const result = await response.json();
      setAllocationResult(result);
    } catch (err) {
      console.error('Allocation processing error:', err);
      setProcessingError(err instanceof Error ? err.message : "Unknown error occurred");
    } finally {
      setIsProcessing(false);
    }
  };

  const fetchFireData = async () => {
    if (!mapLocation) {
      alert('Please search for a location first');
      return;
    }
    
    setIsLoadingFires(true);
    setFireError('');
    
    try {
      const buffer = 10.0; 
      const north = mapLocation[0] + buffer;
      const south = mapLocation[0] - buffer;
      const east = mapLocation[1] + buffer;
      const west = mapLocation[1] - buffer;
      
      console.log("Using coordinates for fire search:", { north, south, east, west });
      
      const today = new Date();
      const sixtyDaysAgo = new Date(today);
      sixtyDaysAgo.setDate(today.getDate() - 60);
      
      const formatDate = (date: Date) => {
        return date.toISOString().split('T')[0];
      };
      
      // NASA FIRMS API URL
      const apiKey = '51cdb5a8cc3991d9f779cc2ed369f848';
      const url = `https://firms.modaps.eosdis.nasa.gov/api/area/csv/${apiKey}/MODIS_NRT/${west},${south},${east},${north}/${formatDate(sixtyDaysAgo)}..${formatDate(today)}`;
      
      console.log("Fetching fire data from URL:", url);
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch fire data: ${response.status}`);
      }
      
      const text = await response.text();
      console.log("Raw CSV response:", text);
      
      if (!text.includes(',') || !text.includes('\n')) {
        console.log("No data from API, creating test data from highest risk location");
        
        // Find highest risk location near the current map location
        const highestRiskLocation: any = await findHighestRiskLocation(mapLocation[0], mapLocation[1]);
        
        if (highestRiskLocation) {
          // Create a test fire at the highest risk location
          const testData = [{
            latitude: parseFloat(highestRiskLocation.LATITUDE),
            longitude: parseFloat(highestRiskLocation.LONGITUDE),
            acq_date: formatDate(new Date()),
            acq_time: "1500",
            satellite: "Test",
            confidence: "High",
            daynight: "D",
            risk_score: highestRiskLocation.RISK_SCORE,
            census_tract: highestRiskLocation.CENSUS_TRACT_ID
          }];
          
          setFires(testData);
          alert(`No real fire data available. Created a test fire at the highest risk location (Risk Score: ${highestRiskLocation.RISK_SCORE}).`);
        } else {
          // Fallback to a test fire at the current location
          const testData = [{
            latitude: mapLocation[0],
            longitude: mapLocation[1],
            acq_date: formatDate(new Date()),
            acq_time: "1500",
            satellite: "Test",
            confidence: "High",
            daynight: "D"
          }];
          
          setFires(testData);
          alert("No real fire data or risk data available. Created a test fire at the current location.");
        }
        
        setIsLoadingFires(false);
        return;
      }
      
      const parsedData = parseCSV(text);
      console.log("Parsed fire data:", parsedData);
      
      if (parsedData && parsedData.length > 0) {
        setFires(parsedData);
        alert(`Found ${parsedData.length} active fires in the search area!`);
      } else {
        console.log("No fires found in the parsed data, creating a test fire at the highest risk location");
        
        const highestRiskLocation: any = await findHighestRiskLocation(mapLocation[0], mapLocation[1]);
        
        if (highestRiskLocation) {
          const testData = [{
            latitude: parseFloat(highestRiskLocation.LATITUDE),
            longitude: parseFloat(highestRiskLocation.LONGITUDE),
            acq_date: formatDate(new Date()),
            acq_time: "1500",
            satellite: "Test",
            confidence: "High",
            daynight: "D",
            risk_score: highestRiskLocation.RISK_SCORE,
            census_tract: highestRiskLocation.CENSUS_TRACT_ID
          }];
          
          setFires(testData);
          alert(`No real fire data available. Created a test fire at the highest risk location (Risk Score: ${highestRiskLocation.RISK_SCORE}).`);
        } else {
          const testData = [{
            latitude: mapLocation[0],
            longitude: mapLocation[1],
            acq_date: formatDate(new Date()),
            acq_time: "1500",
            satellite: "Test",
            confidence: "High",
            daynight: "D"
          }];
          
          setFires(testData);
          alert("No real fire data or risk data available. Created a test fire at the current location.");
        }
      }
    } catch (err) {
      console.error('Error fetching fire data:', err);
      setFireError(err instanceof Error ? err.message : 'Failed to fetch fire data');
      
      try {
        const highestRiskLocation: any = await findHighestRiskLocation(mapLocation[0], mapLocation[1]);
        
        if (highestRiskLocation) {
          const testData = [{
            latitude: parseFloat(highestRiskLocation.LATITUDE),
            longitude: parseFloat(highestRiskLocation.LONGITUDE),
            acq_date: new Date().toISOString().split('T')[0],
            acq_time: "1500",
            satellite: "Test",
            confidence: "High",
            daynight: "D",
            risk_score: highestRiskLocation.RISK_SCORE,
            census_tract: highestRiskLocation.CENSUS_TRACT_ID
          }];
          
          setFires(testData);
          alert(`Error fetching fire data. Created a test fire at the highest risk location (Risk Score: ${highestRiskLocation.RISK_SCORE}).`);
        } else {
          const testData = [{
            latitude: mapLocation[0],
            longitude: mapLocation[1],
            acq_date: new Date().toISOString().split('T')[0],
            acq_time: "1500",
            satellite: "Test",
            confidence: "High",
            daynight: "D"
          }];
          
          setFires(testData);
          alert("Error fetching fire data and no risk data available. Created a test fire at the current location.");
        }
      } catch (highRiskErr) {
        console.error('Error creating high-risk test fire:', highRiskErr);
        
        const testData = [{
          latitude: mapLocation[0],
          longitude: mapLocation[1],
          acq_date: new Date().toISOString().split('T')[0],
          acq_time: "1500",
          satellite: "Test",
          confidence: "High",
          daynight: "D"
        }];
        
        setFires(testData);
        alert("Multiple errors occurred. Created a test fire at the current location.");
      }
    } finally {
      setIsLoadingFires(false);
    }
  };

  return (
    <ChakraProvider value={defaultSystem}>
      <Box className="app-background" minHeight="100vh" py={8}>
        <Container maxW="container.md">
          <VStack align="center" mb={8}>
            <Heading as="h1" size="2xl" color="teal.600">
              Dispatch Services
            </Heading>
            <Text fontSize="lg" color="gray.600" textAlign="center">
              Intelligent allocation of emergency services during natural disasters.
            </Text>
          </VStack>
          
          <Box 
            bg="white" 
            p={8} 
            borderRadius="lg" 
            boxShadow="lg"
            width="100%" 
            maxWidth="500px" 
            mx="auto"
            mb={6}
          >
            <VStack>
              <Input
                placeholder="Enter location (e.g., Los Angeles, CA)"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                size="lg"
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button 
                onClick={handleSearch} 
                colorScheme="teal" 
                width="100%"
                size="lg"
                _hover={{ bg: "teal.500" }}
                loading={isLoading}
              >
                Search
              </Button>
              {error && <Text color="red.500">{error}</Text>}
            </VStack>
          </Box>
          
          {isLoading && (
            <Box textAlign="center" mt={8}>
              <Spinner size="xl" color="teal.500" />
              <Text mt={2}>Searching for location...</Text>
            </Box>
          )}
          
          {mapLocation && (
            <>
              <Box 
                width="100%" 
                height="600px" 
                borderRadius="lg" 
                overflow="hidden" 
                boxShadow="lg" 
                mt={6}
                mb={4}
                position="relative"
              >
                <Text 
                  position="absolute" 
                  top="10px" 
                  left="50%" 
                  transform="translateX(-50%)" 
                  bg="rgba(255,255,255,0.8)" 
                  px={3} 
                  py={1} 
                  borderRadius="md" 
                  zIndex={1000}
                  fontSize="sm"
                >
                  Move the map to position the red box over your target area
                </Text>
                <MapContainer 
                  center={mapLocation} 
                  zoom={13} 
                  style={{ height: '100%', width: '100%' }}
                  zoomDelta={0.35}
                  zoomSnap={0.35}
                  wheelPxPerZoomLevel={100}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <Marker position={mapLocation}>
                    <Popup>
                      <Text fontWeight="bold">{locationName}</Text>
                    </Popup>
                  </Marker>
                  <FixedBoundingBox onBoundsChange={setBoundingBox} />
                  {allocationResult && allocationResult.graph_data && (
                    <GraphVisualization 
                      graphData={allocationResult.graph_data} 
                      fires={fires}
                    />
                  )}
                  {allocationResult && allocationResult.fire_stations && (
                    <FireStationMarkers stations={allocationResult.fire_stations} />
                  )}
                  {fires.length > 0 && (
                    <FireMarkers fires={fires} />
                  )}
                </MapContainer>
              </Box>
              
              <Flex width="100%" maxWidth="500px" mx="auto" gap={4}>
                <Button
                  onClick={processAllocation}
                  colorScheme="blue"
                  size="lg"
                  flex="1"
                  loading={isProcessing}
                  loadingText="Processing"
                >
                  Process Relief Route Allocation
                </Button>
                
                <Button
                  onClick={fetchFireData}
                  colorScheme="red"
                  size="lg"
                  flex="1"
                  loading={isLoadingFires}
                  loadingText="Checking"
                >
                  Update On Fire Status
                </Button>
              </Flex>
              
              {processingError && (
                <Text color="red.500" textAlign="center" mt={2}>
                  {processingError}
                </Text>
              )}
              
              {isProcessing && (
                <Box textAlign="center" mt={4}>
                  <Text>Calculating optimal resource allocation...</Text>
                </Box>
              )}
              
              {allocationResult && (
                <Box 
                  mt={6} 
                  p={6} 
                  bg="white" 
                  borderRadius="lg" 
                  boxShadow="md"
                >
                  <Heading size="md" mb={4}>Allocation Results</Heading>
                  <Text>
                    The backend has processed the allocation for {locationName}.
                  </Text>
                  <Text mt={2}>
                    Area processed: {allocationResult.bbox[0].toFixed(6)}, {allocationResult.bbox[2].toFixed(6)} to {allocationResult.bbox[1].toFixed(6)}, {allocationResult.bbox[3].toFixed(6)}
                  </Text>
                  <Text mt={2}>
                    Network nodes: {allocationResult.nodes_count}
                  </Text>
                  <Text mt={2}>
                    Network edges: {allocationResult.edges_count}
                  </Text>
                </Box>
              )}
            </>
          )}
        </Container>
      </Box>
    </ChakraProvider>
  );
}

export default App;

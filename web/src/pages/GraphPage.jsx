import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import api from '../api';
import { RefreshCw, ZoomIn, ZoomOut, Maximize, Share2, Info, Layout } from 'lucide-react';

const GraphPage = () => {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const fgRef = useRef();
    const [containerDimensions, setContainerDimensions] = useState({ width: 0, height: 0 });
    const containerRef = useRef(null);

    useEffect(() => {
        fetchGraphData();

        const updateDimensions = () => {
            if (containerRef.current) {
                setContainerDimensions({
                    width: containerRef.current.offsetWidth,
                    height: containerRef.current.offsetHeight
                });
            }
        };

        window.addEventListener('resize', updateDimensions);
        updateDimensions();

        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    const fetchGraphData = async () => {
        setLoading(true);
        try {
            const response = await api.get('/graph/data');
            setGraphData(response.data);
        } catch (error) {
            console.error("Failed to fetch graph data", error);
        }
        setLoading(false);
    };

    const handleZoomIn = () => {
        fgRef.current.zoom(fgRef.current.zoom() * 1.2, 400);
    };

    const handleZoomOut = () => {
        fgRef.current.zoom(fgRef.current.zoom() / 1.2, 400);
    };

    const handleFit = () => {
        fgRef.current.zoomToFit(400);
    };

    return (
        <div className="h-[calc(100vh-140px)] flex flex-col bg-white rounded-[28px] shadow-sm overflow-hidden border border-secondary-200 animate-fade-in mt-6 relative mx-4 lg:mx-0">
            {/* Floating Toolbar */}
            <div className="absolute top-4 left-4 right-4 z-10 flex justify-between items-start pointer-events-none">
                <div className="pointer-events-auto bg-white/90 backdrop-blur-md p-4 rounded-[20px] shadow-md border border-secondary-100 flex items-center">
                    <div className="h-10 w-10 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center mr-3">
                        <Share2 size={20} />
                    </div>
                    <div>
                        <h1 className="text-base font-bold text-secondary-900 leading-none">Graph Explorer</h1>
                        <p className="text-xs text-secondary-500 mt-1 font-medium">
                            {graphData.nodes.length} Nodes • {graphData.links.length} Relations
                        </p>
                    </div>
                </div>

                <div className="pointer-events-auto bg-white/90 backdrop-blur-md p-1.5 rounded-full shadow-md border border-secondary-100 flex flex-col gap-1.5">
                    <button
                        onClick={fetchGraphData}
                        className="p-2.5 rounded-full hover:bg-secondary-100 text-secondary-600 transition-all hover:text-primary-600"
                        title="Refresh"
                    >
                        <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                    <button
                        onClick={handleZoomIn}
                        className="p-2.5 rounded-full hover:bg-secondary-100 text-secondary-600 transition-all hover:text-primary-600"
                        title="Zoom In"
                    >
                        <ZoomIn size={20} />
                    </button>
                    <button
                        onClick={handleZoomOut}
                        className="p-2.5 rounded-full hover:bg-secondary-100 text-secondary-600 transition-all hover:text-primary-600"
                        title="Zoom Out"
                    >
                        <ZoomOut size={20} />
                    </button>
                    <button
                        onClick={handleFit}
                        className="p-2.5 rounded-full hover:bg-secondary-100 text-secondary-600 transition-all hover:text-primary-600"
                        title="Fit View"
                    >
                        <Maximize size={20} />
                    </button>
                </div>
            </div>

            <div className="flex-grow relative bg-[#0a0f1c]" ref={containerRef}>
                {loading && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center z-10 bg-[#0a0f1c]/80 backdrop-blur-sm">
                        <RefreshCw className="animate-spin text-primary-400 mb-4" size={48} />
                        <span className="text-primary-100 font-medium tracking-wide">Fetching Graph Data...</span>
                    </div>
                )}

                {!loading && graphData.nodes.length === 0 && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center z-10 text-secondary-500">
                        <Layout size={64} className="mb-6 opacity-20" />
                        <p className="text-lg font-medium text-secondary-400">Visualization Empty</p>
                        <p className="text-sm opacity-60">Upload documents to populate the graph.</p>
                    </div>
                )}

                {!loading && containerDimensions.width > 0 && (
                    <ForceGraph2D
                        ref={fgRef}
                        width={containerDimensions.width}
                        height={containerDimensions.height}
                        graphData={graphData}
                        nodeLabel="label"
                        nodeAutoColorBy="group"
                        linkDirectionalArrowLength={3.5}
                        linkDirectionalArrowRelPos={1}
                        backgroundColor="#0a0f1c"
                        linkColor={() => 'rgba(255,255,255,0.15)'}
                        nodeCanvasObject={(node, ctx, globalScale) => {
                            const label = node.label;
                            const fontSize = 12 / globalScale;
                            ctx.font = `${fontSize}px Sans-Serif`;
                            const textWidth = ctx.measureText(label).width;
                            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.4); // Add padding

                            ctx.fillStyle = 'rgba(10, 15, 28, 0.9)'; // Dark background for text
                            // Rounded rect for label
                            const x = node.x - bckgDimensions[0] / 2;
                            const y = node.y - bckgDimensions[1] / 2;
                            const w = bckgDimensions[0];
                            const h = bckgDimensions[1];
                            const r = 4 / globalScale; // Corner radius

                            ctx.beginPath();
                            ctx.moveTo(x + r, y);
                            ctx.lineTo(x + w - r, y);
                            ctx.quadraticCurveTo(x + w, y, x + w, y + r);
                            ctx.lineTo(x + w, y + h - r);
                            ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
                            ctx.lineTo(x + r, y + h);
                            ctx.quadraticCurveTo(x, y + h, x, y + h - r);
                            ctx.lineTo(x, y + r);
                            ctx.quadraticCurveTo(x, y, x + r, y);
                            ctx.closePath();
                            ctx.fill();

                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'middle';
                            ctx.fillStyle = node.color; // Text color matches node
                            ctx.fillText(label, node.x, node.y);

                            node.__bckgDimensions = bckgDimensions;
                        }}
                        nodePointerAreaPaint={(node, color, ctx) => {
                            ctx.fillStyle = color;
                            const bckgDimensions = node.__bckgDimensions;
                            bckgDimensions && ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
                        }}
                    />
                )}
            </div>
        </div>
    );
};

export default GraphPage;

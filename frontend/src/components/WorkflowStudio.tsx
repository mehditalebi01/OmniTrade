import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  addEdge, Background, Controls, MiniMap, ReactFlow, useEdgesState, useNodesState,
  type Connection, type Edge, type EdgeChange, type Node, type NodeChange,
} from '@xyflow/react';
import { Alert, Box, Button, Card, Chip, CircularProgress, Divider, MenuItem, Select, Stack, TextField, Typography } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import PublishIcon from '@mui/icons-material/Publish';
import SaveIcon from '@mui/icons-material/Save';
import VerifiedIcon from '@mui/icons-material/Verified';
import UndoIcon from '@mui/icons-material/Undo';
import RedoIcon from '@mui/icons-material/Redo';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import PaletteIcon from '@mui/icons-material/Palette';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import { createSample, getCatalog, listWorkflows, publishWorkflow, resetWorkflowDefault, updateWorkflow, validateWorkflow } from '../api';
import type { CatalogSuggestion, ValidationResult, WorkflowRecord } from '../types';
import { activeWorkflow } from '../workflows';

type Catalog = Awaited<ReturnType<typeof getCatalog>>['nodes'];
type RawNode = { id: string; name: string; type: string; config: Record<string, unknown>; failure_policy: string; timeout_seconds: number; retry: Record<string, unknown>; position: { x: number; y: number } };
type RawEdge = { id: string; source: string; source_port: string; target: string; target_port: string; loop: boolean };
type Snapshot = { nodes: Node[]; edges: Edge[] };

const groupColors: Record<string, string> = { control: '#7c6cff', evidence: '#f5a623', normalization: '#30b7e8', calculation: '#1ec9a1', specialist: '#b98cff', research: '#35cc61', risk: '#ff6678', output: '#5482ff' };

export default function WorkflowStudio() {
  const [workflow, setWorkflow] = useState<WorkflowRecord>();
  const [catalog, setCatalog] = useState<Catalog>({});
  const [selectedType, setSelectedType] = useState('fetch_market');
  const [selectedNodeId, setSelectedNodeId] = useState<string>();
  const [validation, setValidation] = useState<ValidationResult>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [connectionAdvice, setConnectionAdvice] = useState('Select a node to see compatible next steps.');
  const [nodeName, setNodeName] = useState('');
  const [nodeColor, setNodeColor] = useState('#7c6cff');
  const [nodes, setNodes, onNodesChangeBase] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChangeBase] = useEdgesState<Edge>([]);
  const history = useRef<Snapshot[]>([]);
  const future = useRef<Snapshot[]>([]);
  const [, setHistoryTick] = useState(0);

  const snapshot = useCallback((): Snapshot => ({
    nodes: nodes.map((node) => ({ ...node, position: { ...node.position }, data: { ...node.data } })),
    edges: edges.map((edge) => ({ ...edge, data: { ...edge.data } })),
  }), [nodes, edges]);
  const remember = useCallback(() => { history.current = [...history.current.slice(-49), snapshot()]; future.current = []; setHistoryTick((value) => value + 1); }, [snapshot]);
  const undo = useCallback(() => { const previous = history.current.pop(); if (!previous) return; future.current.push(snapshot()); setNodes(previous.nodes); setEdges(previous.edges); setValidation(undefined); setHistoryTick((value) => value + 1); }, [setEdges, setNodes, snapshot]);
  const redo = useCallback(() => { const next = future.current.pop(); if (!next) return; history.current.push(snapshot()); setNodes(next.nodes); setEdges(next.edges); setValidation(undefined); setHistoryTick((value) => value + 1); }, [setEdges, setNodes, snapshot]);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [all, nodeCatalog] = await Promise.all([listWorkflows(), getCatalog()]);
      const current = activeWorkflow(all) ?? await createSample();
      setCatalog(nodeCatalog.nodes);
      setWorkflow(current);
      const graph = toFlow(current, nodeCatalog.nodes);
      setNodes(graph.nodes);
      setEdges(graph.edges);
      history.current = [];
      future.current = [];
    } catch (reason) { setError(String(reason)); } finally { setBusy(false); }
  }, [setEdges, setNodes]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      if (event.key.toLowerCase() === 'z') { event.preventDefault(); event.shiftKey ? redo() : undo(); }
      else if (event.key.toLowerCase() === 'y') { event.preventDefault(); redo(); }
    };
    window.addEventListener('keydown', key);
    return () => window.removeEventListener('keydown', key);
  }, [redo, undo]);

  const selectedNode = nodes.find((node) => node.id === selectedNodeId);
  const selectedNodeType = String(selectedNode?.data.nodeType ?? '');
  useEffect(() => {
    if (!selectedNode) return;
    setNodeName(String(selectedNode.data.label ?? ''));
    setNodeColor(String(selectedNode.style?.background ?? '#7c6cff'));
  }, [selectedNode]);
  const suggestions = useMemo(() => {
    const raw = catalog[selectedNodeType]?.suggested_targets ?? [];
    const unique = new Map<string, CatalogSuggestion>();
    raw.forEach((suggestion) => { if (!unique.has(suggestion.node_type)) unique.set(suggestion.node_type, suggestion); });
    return [...unique.values()].slice(0, 8);
  }, [catalog, selectedNodeType]);

  const nodeChanges = useCallback((changes: NodeChange[]) => { if (changes.some((change) => change.type === 'remove')) remember(); onNodesChangeBase(changes); setValidation(undefined); }, [onNodesChangeBase, remember]);
  const edgeChanges = useCallback((changes: EdgeChange[]) => { if (changes.some((change) => change.type === 'remove')) remember(); onEdgesChangeBase(changes); setValidation(undefined); }, [onEdgesChangeBase, remember]);

  const compatibleConnection = useCallback((sourceId: string, targetId: string) => {
    const sourceType = String(nodes.find((node) => node.id === sourceId)?.data.nodeType ?? '');
    const targetType = String(nodes.find((node) => node.id === targetId)?.data.nodeType ?? '');
    return (catalog[sourceType]?.suggested_targets ?? []).find((item) => item.node_type === targetType) as CatalogSuggestion | undefined;
  }, [catalog, nodes]);

  const addCompatibleEdge = useCallback((sourceId: string, targetId: string, suggestion: CatalogSuggestion) => {
    const duplicate = edges.some((edge) => edge.source === sourceId && edge.target === targetId && edge.data?.source_port === suggestion.source_port && edge.data?.target_port === suggestion.target_port);
    if (duplicate) { setConnectionAdvice('This compatible connection already exists.'); return; }
    setEdges((current) => addEdge({ id: `edge-${crypto.randomUUID()}`, source: sourceId, target: targetId, data: { source_port: suggestion.source_port, target_port: suggestion.target_port, loop: false }, animated: true, style: { stroke: '#35cc61' } }, current));
    setConnectionAdvice(`Connected ${suggestion.source_port} to ${suggestion.target_port} using ${suggestion.data_type}.`);
    setValidation(undefined);
  }, [edges, setEdges]);

  const onConnect = useCallback((connection: Connection) => {
    if (!connection.source || !connection.target) return;
    const suggestion = compatibleConnection(connection.source, connection.target);
    if (!suggestion) {
      const sourceType = String(nodes.find((node) => node.id === connection.source)?.data.nodeType ?? 'source');
      const targetType = String(nodes.find((node) => node.id === connection.target)?.data.nodeType ?? 'target');
      setConnectionAdvice(`${sourceType} cannot connect to ${targetType}. Select the source node and use a recommended next node.`);
      return;
    }
    remember();
    addCompatibleEdge(connection.source, connection.target, suggestion);
  }, [addCompatibleEdge, compatibleConnection, nodes, remember]);

  function createNode(type: string, position?: { x: number; y: number }) {
    const id = `${type}-${crypto.randomUUID().slice(0, 8)}`;
    const definition: RawNode = { id, type, name: defaultNodeName(type), config: defaultConfig(type), failure_policy: 'required', timeout_seconds: 30, retry: { max_attempts: 1, backoff_ms: 100 }, position: position ?? { x: 80 + nodes.length * 12, y: 80 + nodes.length * 8 } };
    setNodes((current) => [...current, flowNode(definition, catalog[type]?.group ?? 'control')]);
    setValidation(undefined);
    return id;
  }

  function addNode() { remember(); createNode(selectedType); }
  function addSuggestedNode(suggestion: CatalogSuggestion) {
    if (!selectedNode) return;
    remember();
    const targetId = createNode(suggestion.node_type, { x: selectedNode.position.x + 230, y: selectedNode.position.y + 100 });
    addCompatibleEdge(selectedNode.id, targetId, suggestion);
    setSelectedNodeId(targetId);
  }

  function applyNodeAppearance() {
    if (!selectedNode || !nodeName.trim()) return;
    remember();
    setNodes((current) => current.map((node) => {
      if (node.id !== selectedNode.id) return node;
      const currentDefinition = node.data.definition as RawNode;
      const definition = { ...currentDefinition, name: nodeName.trim(), config: { ...currentDefinition.config, ui_color: nodeColor } };
      return { ...node, data: { ...node.data, label: definition.name, definition }, style: { ...node.style, background: nodeColor, color: readableText(nodeColor) } };
    }));
    setValidation(undefined);
  }

  function deleteSelectedNode() {
    if (!selectedNode) return;
    remember();
    setNodes((current) => current.filter((node) => node.id !== selectedNode.id));
    setEdges((current) => current.filter((edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id));
    setSelectedNodeId(undefined);
    setValidation(undefined);
  }

  function resetSelectedNode() {
    if (!selectedNode) return;
    const group = catalog[selectedNodeType]?.group ?? 'control';
    const name = defaultNodeName(selectedNodeType);
    const color = groupColors[group];
    remember();
    setNodes((current) => current.map((node) => {
      if (node.id !== selectedNode.id) return node;
      const currentDefinition = node.data.definition as RawNode;
      const config = { ...currentDefinition.config };
      delete config.ui_color;
      const definition = { ...currentDefinition, name, config };
      return { ...node, data: { ...node.data, label: name, definition }, style: { ...node.style, background: color, color: readableText(color) } };
    }));
    setNodeName(name);
    setNodeColor(color);
    setValidation(undefined);
  }

  async function resetGraph() {
    if (!workflow || !window.confirm('Reset this draft to the complete default workflow? Published versions and old reports will stay unchanged.')) return;
    setBusy(true); setError('');
    try {
      remember();
      const updated = await resetWorkflowDefault(workflow.id);
      const graph = toFlow(updated, catalog);
      setWorkflow(updated); setNodes(graph.nodes); setEdges(graph.edges); setSelectedNodeId(undefined); setValidation(undefined);
    } catch (reason) { setError(String(reason)); } finally { setBusy(false); }
  }

  function definition() {
    if (!workflow) throw new Error('Workflow is not loaded');
    const original = workflow.definition as unknown as { nodes: RawNode[]; edges: RawEdge[] };
    return {
      ...workflow.definition,
      nodes: nodes.map((node) => { const old = original.nodes.find((item) => item.id === node.id); const current = node.data.definition as RawNode; return { ...(old ?? current), ...current, name: String(node.data.label), position: node.position }; }),
      edges: edges.map((edge) => { const old = original.edges.find((item) => item.id === edge.id); return old ? { ...old, source: edge.source, target: edge.target, source_port: String(edge.data?.source_port ?? old.source_port), target_port: String(edge.data?.target_port ?? old.target_port) } : { id: edge.id, source: edge.source, target: edge.target, source_port: String(edge.data?.source_port), target_port: String(edge.data?.target_port), loop: Boolean(edge.data?.loop) }; }),
    };
  }

  async function saveDraft() { if (!workflow) throw new Error('Workflow is not loaded'); const updated = await updateWorkflow(workflow.id, definition()); setWorkflow(updated); return updated; }
  async function save() { setBusy(true); setError(''); try { await saveDraft(); setValidation(undefined); } catch (reason) { setError(String(reason)); } finally { setBusy(false); } }
  async function validate() { if (!workflow) return; setBusy(true); setError(''); try { await saveDraft(); setValidation(await validateWorkflow(workflow.id)); } catch (reason) { setError(String(reason)); } finally { setBusy(false); } }
  async function publish() { if (!workflow) return; setBusy(true); try { await saveDraft(); const checked = await validateWorkflow(workflow.id); setValidation(checked); if (!checked.valid) return; const version = await publishWorkflow(workflow.id); setWorkflow((current) => current ? { ...current, published_version_id: version.id } : current); } catch (reason) { setError(String(reason)); } finally { setBusy(false); } }

  return <Stack spacing={1.5}>
    <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ md: 'center' }} gap={1}>
      <Box><Typography variant="h4" fontWeight={800}>Advanced Workflow Lab</Typography><Typography color="text.secondary">Edit the real published workflow. Smart suggestions use the same port rules as the backend validator.</Typography></Box>
      <Stack direction="row" spacing={1} flexWrap="wrap"><Button startIcon={<UndoIcon />} disabled={!history.current.length} onClick={undo}>Undo</Button><Button startIcon={<RedoIcon />} disabled={!future.current.length} onClick={redo}>Redo</Button><Button color="warning" startIcon={<RestartAltIcon />} onClick={resetGraph}>Reset graph</Button><Button variant="outlined" startIcon={<SaveIcon />} onClick={save}>Save</Button><Button variant="outlined" startIcon={<VerifiedIcon />} onClick={validate}>Validate</Button><Button variant="contained" startIcon={<PublishIcon />} disabled={!validation?.valid} onClick={publish}>Publish</Button></Stack>
    </Stack>
    <Alert severity="info">Draft edits affect analysis only after validation and publication. Every run executes its saved workflow version.</Alert>
    {error && <Alert severity="error">{error}</Alert>}
    {validation && <Alert severity={validation.valid ? 'success' : 'error'}>{validation.valid ? 'Graph is valid' : <Box><b>{validation.errors.length} validation errors</b>{validation.errors.slice(0, 5).map((issue) => <div key={`${issue.code}-${issue.node_id}-${issue.edge_id}`}>{issue.message}</div>)}</Box>}</Alert>}
    <Card sx={{ height: 'calc(100vh - 230px)', minHeight: 680, overflow: 'hidden' }}>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '320px 1fr' }, height: '100%' }}>
        <Box sx={{ p: 2, borderRight: '1px solid #263554', overflow: 'auto' }}>
          <Typography fontWeight={800}>Node catalog</Typography><Typography variant="caption" color="text.secondary">Typed workflow components</Typography>
          <Stack direction="row" spacing={1} sx={{ my: 1.5 }}><Select size="small" fullWidth value={selectedType} onChange={(event) => setSelectedType(event.target.value)}>{Object.keys(catalog).sort().map((type) => <MenuItem key={type} value={type}>{type.replaceAll('_', ' ')}</MenuItem>)}</Select><Button variant="contained" aria-label="Add node" onClick={addNode}><AddIcon /></Button></Stack>
          <Divider sx={{ mb: 1.5 }} />
          {selectedNode ? <Stack spacing={1.2}>
            <Typography fontWeight={900}>Selected node</Typography>
            <TextField size="small" label="Node name" value={nodeName} inputProps={{ maxLength: 120 }} onChange={(event) => setNodeName(event.target.value)} />
            <TextField size="small" type="color" label="Node color" value={nodeColor} onChange={(event) => setNodeColor(event.target.value)} InputLabelProps={{ shrink: true }} />
            <Stack direction="row" flexWrap="wrap" gap={.7}>
              <Button size="small" variant="contained" startIcon={<PaletteIcon />} disabled={!nodeName.trim()} onClick={applyNodeAppearance}>Apply name/color</Button>
              <Button size="small" variant="outlined" startIcon={<RestartAltIcon />} onClick={resetSelectedNode}>Reset node</Button>
              <Button size="small" color="error" variant="outlined" startIcon={<DeleteOutlineIcon />} onClick={deleteSelectedNode}>Delete</Button>
            </Stack>
            <Divider />
            <Stack direction="row" alignItems="center" gap={1}><AutoFixHighIcon color="secondary" /><Typography fontWeight={900}>Smart next nodes</Typography></Stack>
            <Typography variant="body2"><b>{String(selectedNode.data.label)}</b><br />Type: {selectedNodeType}</Typography>
            <Alert severity="info" icon={false}>
              <Typography variant="subtitle2" fontWeight={800}>What this node does</Typography>
              <Typography variant="body2">{catalog[selectedNodeType]?.description ?? 'No description is available.'}</Typography>
            </Alert>
            {suggestions.length ? suggestions.map((suggestion) => <Button key={`${suggestion.node_type}-${suggestion.source_port}-${suggestion.target_port}`} variant="outlined" onClick={() => addSuggestedNode(suggestion)} sx={{ justifyContent: 'flex-start', textAlign: 'left' }}><Box><b>Add {suggestion.node_type.replaceAll('_', ' ')}</b><br /><Typography component="span" variant="caption">{suggestion.source_port} → {suggestion.target_port} ({suggestion.data_type})</Typography></Box></Button>) : <Alert severity="info">This node has no compatible next node. It may be an end node.</Alert>}
          </Stack> : <Typography variant="body2" color="text.secondary">Select a graph node to see safe next steps.</Typography>}
          <Alert severity={connectionAdvice.includes('cannot') ? 'warning' : 'info'} sx={{ mt: 2 }}>{connectionAdvice}</Alert>
          <Divider sx={{ my: 1.5 }} />
          <Stack direction="row" flexWrap="wrap" gap={.7}>{Object.entries(groupColors).map(([name, color]) => <Chip key={name} size="small" label={name} sx={{ background: color, color: '#06101d', fontWeight: 800 }} />)}</Stack>
          <Typography display="block" variant="caption" color="text.secondary" sx={{ mt: 1.5 }}>Move, connect, or delete nodes. Ctrl+Z undoes a change. Save, validate, then publish to use it in analysis.</Typography>
        </Box>
        <Box sx={{ position: 'relative', minHeight: 500 }}>{busy && !workflow ? <Box sx={{ display: 'grid', placeItems: 'center', height: '100%' }}><CircularProgress /></Box> : <ReactFlow nodes={nodes} edges={edges} onNodesChange={nodeChanges} onEdgesChange={edgeChanges} onConnect={onConnect} onNodeClick={(_, node) => setSelectedNodeId(node.id)} onPaneClick={() => setSelectedNodeId(undefined)} onNodeDragStart={remember} fitView deleteKeyCode="Delete"><Background color="#31415f" /><MiniMap nodeColor={(node) => String(node.style?.background ?? '#777')} /><Controls /></ReactFlow>}</Box>
      </Box>
    </Card>
  </Stack>;
}

function toFlow(workflow: WorkflowRecord, catalog: Catalog): Snapshot {
  const raw = workflow.definition as unknown as { nodes: RawNode[]; edges: RawEdge[] };
  return {
    nodes: raw.nodes.map((node, index) => flowNode({ ...node, position: node.position.x || node.position.y ? node.position : { x: (index % 6) * 190, y: Math.floor(index / 6) * 120 } }, catalog[node.type]?.group ?? 'control')),
    edges: raw.edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target, animated: true, data: { source_port: edge.source_port, target_port: edge.target_port, loop: edge.loop }, style: { stroke: '#8aa0c8' } })),
  };
}
function flowNode(definition: RawNode, group: string): Node { const background = typeof definition.config.ui_color === 'string' ? definition.config.ui_color : groupColors[group]; return { id: definition.id, position: definition.position, data: { label: definition.name, nodeType: definition.type, definition }, style: { background, color: readableText(background), fontWeight: 800, width: 165, borderRadius: 12 } }; }
function defaultConfig(type: string): Record<string, unknown> { if (type === 'bounded_loop') return { max_iterations: 2 }; if (type === 'join') return { join_policy: 'required' }; if (type === 'time_guard') return { max_age_hours: 72 }; return {}; }
function defaultNodeName(type: string): string { return type.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function readableText(color: string): string { const hex = color.replace('#', ''); if (!/^[0-9a-f]{6}$/i.test(hex)) return '#06101d'; const [red, green, blue] = [0, 2, 4].map((index) => Number.parseInt(hex.slice(index, index + 2), 16)); return (red * 299 + green * 587 + blue * 114) / 1000 > 145 ? '#06101d' : '#ffffff'; }

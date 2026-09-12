package omnitrade.vp;

import com.vp.plugin.ApplicationManager;
import com.vp.plugin.DiagramManager;
import com.vp.plugin.ProjectManager;
import com.vp.plugin.VPPlugin;
import com.vp.plugin.VPPluginCommandLineSupport;
import com.vp.plugin.VPPluginInfo;
import com.vp.plugin.diagram.IActivityDiagramUIModel;
import com.vp.plugin.diagram.IClassDiagramUIModel;
import com.vp.plugin.diagram.ICommunicationDiagramUIModel;
import com.vp.plugin.diagram.ICompositeStructureDiagramUIModel;
import com.vp.plugin.diagram.IComponentDiagramUIModel;
import com.vp.plugin.diagram.IConnectorUIModel;
import com.vp.plugin.diagram.IDiagramElement;
import com.vp.plugin.diagram.IDiagramUIModel;
import com.vp.plugin.diagram.IInteractionDiagramUIModel;
import com.vp.plugin.diagram.IInteractionOverviewDiagramUIModel;
import com.vp.plugin.diagram.IDeploymentDiagramUIModel;
import com.vp.plugin.diagram.IObjectDiagramUIModel;
import com.vp.plugin.diagram.IOverviewDiagramUIModel;
import com.vp.plugin.diagram.IPackageDiagramUIModel;
import com.vp.plugin.diagram.IShapeUIModel;
import com.vp.plugin.diagram.IStateDiagramUIModel;
import com.vp.plugin.diagram.ITimingDiagramUIModel;
import com.vp.plugin.diagram.IUseCaseDiagramUIModel;
import com.vp.plugin.diagram.connector.IMessageUIModel;
import com.vp.plugin.diagram.shape.IActivationUIModel;
import com.vp.plugin.diagram.shape.IClassUIModel;
import com.vp.plugin.diagram.shape.IComponentUIModel;
import com.vp.plugin.diagram.shape.IInstanceSpecificationUIModel;
import com.vp.plugin.diagram.shape.IInteractionOccurrenceUIModel;
import com.vp.plugin.diagram.shape.IInteractionLifeLineUIModel;
import com.vp.plugin.diagram.shape.IStateUIModel;
import com.vp.plugin.diagram.shape.ITimingFrameUIModel;
import com.vp.plugin.model.IActivation;
import com.vp.plugin.model.IActivityFinalNode;
import com.vp.plugin.model.IAttribute;
import com.vp.plugin.model.IAssociation;
import com.vp.plugin.model.IClass;
import com.vp.plugin.model.ICallTrigger;
import com.vp.plugin.model.IComponent;
import com.vp.plugin.model.ICompositeValueSpecification;
import com.vp.plugin.model.IControlFlow;
import com.vp.plugin.model.IDependency;
import com.vp.plugin.model.IDecisionNode;
import com.vp.plugin.model.IFrame;
import com.vp.plugin.model.IInitialNode;
import com.vp.plugin.model.IInstanceSpecification;
import com.vp.plugin.model.IInteractionOccurrence;
import com.vp.plugin.model.IInteractionLifeLine;
import com.vp.plugin.model.IInteractionLifeLineLink;
import com.vp.plugin.model.ILink;
import com.vp.plugin.model.ILifeLine;
import com.vp.plugin.model.IMessage;
import com.vp.plugin.model.IModel;
import com.vp.plugin.model.IModelElement;
import com.vp.plugin.model.INOTE;
import com.vp.plugin.model.INode;
import com.vp.plugin.model.IOperation;
import com.vp.plugin.model.IPackage;
import com.vp.plugin.model.IPort;
import com.vp.plugin.model.ISlot;
import com.vp.plugin.model.IStateCondition;
import com.vp.plugin.model.ITimeInstance;
import com.vp.plugin.model.ITimeUnit;
import com.vp.plugin.model.ITimingFrame;
import com.vp.plugin.model.ITransition2;
import com.vp.plugin.model.factory.IModelElementFactory;

import java.awt.Color;
import java.awt.Point;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Builds the report-aligned OmniTrade model as native Visual Paradigm diagrams. */
public final class OmniTradeDiagramPlugin implements VPPlugin, VPPluginCommandLineSupport {
    private static final String PLUGIN_ID = "omnitrade.report.diagrams";
    // Keep the authored coordinates.  The earlier 0.72 import scale made native
    // captions and connector labels collide after Visual Paradigm applied its
    // own minimum sizes and compartment rules.
    private static final double SCALE = 1.0;
    private static final Color TEXT = Color.decode("#172033");
    private static final Map<String, IClass> CLASSIFIERS = new HashMap<>();
    private static final Map<String, ILifeLine> TIMING_LIFELINES = new HashMap<>();

    @Override
    public void loaded(VPPluginInfo info) {
        // The command-line entry point performs the deterministic import.
    }

    @Override
    public void unloaded() {
    }

    @Override
    public void invoke(String[] args) {
        if (args.length == 1 && args[0].contains("@@@")) {
            args = args[0].split("@@@", -1);
        }
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected: <vp-diagrams.tsv> <output.vpp> [append]"
            );
        }
        boolean append = args.length >= 3 && "append".equalsIgnoreCase(args[2]);
        try {
            build(Path.of(args[0]), new File(args[1]), append);
        } catch (Exception error) {
            error.printStackTrace();
            throw new RuntimeException("OmniTrade Visual Paradigm generation failed", error);
        }
    }

    private void build(Path exchange, File output, boolean append) throws Exception {
        ApplicationManager app = ApplicationManager.instance();
        ProjectManager projectManager = app.getProjectManager();
        DiagramManager diagramManager = app.getDiagramManager();

        // The report generator starts from a clean project. Architecture work can
        // instead append native diagrams to an explicitly opened seed project so
        // the user's existing Atlas and UML inventory remain intact.
        if (!append) {
            projectManager.newProject();
        }
        CLASSIFIERS.clear();
        TIMING_LIFELINES.clear();

        Map<String, IDiagramUIModel> diagrams = new HashMap<>();
        Map<String, String> diagramTypes = new HashMap<>();
        Map<String, Map<String, IDiagramElement>> shapes = new HashMap<>();
        List<String[]> edges = new ArrayList<>();

        for (String raw : Files.readAllLines(exchange, StandardCharsets.UTF_8)) {
            if (raw.isBlank() || raw.startsWith("#")) {
                continue;
            }
            String[] row = raw.split("\\t", -1);
            if ("D".equals(row[0])) {
                String id = decode(row[1]);
                String title = decode(row[2]);
                String type = row[3];
                String subtitle = decode(row[6]);
                IDiagramUIModel diagram = diagramManager.createDiagram(diagramType(type));
                diagram.setName(title);
                diagram.setDocumentation("Generated from " + id + "\n" + subtitle);
                diagram.setDiagramBackground(Color.WHITE);
                if (diagram instanceof IActivityDiagramUIModel) {
                    IActivityDiagramUIModel activity = (IActivityDiagramUIModel) diagram;
                    activity.setShowDiagramFrame(true);
                    activity.setDecisionMergeNodeConnectionPointStyle(
                        IActivityDiagramUIModel.DECISION_MERGE_NODE_CONNECTION_POINT_STYLE_CONNECT_TO_VERTEX);
                    activity.setControlFlowDisplayOption(IActivityDiagramUIModel.CONTROL_FLOW_DISPLAY_OPTION_SOLID_LINE);
                } else if (diagram instanceof IStateDiagramUIModel) {
                    IStateDiagramUIModel state = (IStateDiagramUIModel) diagram;
                    state.setShowDiagramFrame(true);
                    state.setStateUseNameTab(IStateDiagramUIModel.STATE_USE_NAME_TAB_NO);
                    state.setCenterStateCaptionVertically(true);
                    state.setShowTransitionTriggers(true);
                } else if (diagram instanceof ICommunicationDiagramUIModel) {
                    ICommunicationDiagramUIModel communication = (ICommunicationDiagramUIModel) diagram;
                    communication.setShowSequenceNumbers(true);
                    communication.setCreateOneMessagePerDirection(false);
                } else if (diagram instanceof IObjectDiagramUIModel) {
                    ((IObjectDiagramUIModel) diagram).setShowInstanceSpecificationSlots(true);
                } else if (diagram instanceof IComponentDiagramUIModel) {
                    IComponentDiagramUIModel component = (IComponentDiagramUIModel) diagram;
                    component.setShowComponentOperations(true);
                    component.setShowComponentAttributes(false);
                } else if (diagram instanceof IPackageDiagramUIModel) {
                    ((IPackageDiagramUIModel) diagram).setShowDiagramFrame(true);
                }
                diagrams.put(id, diagram);
                diagramTypes.put(id, type);
                shapes.put(id, new HashMap<String, IDiagramElement>());
            } else if ("B".equals(row[0])) {
                if ("SEQUENCE".equals(diagramTypes.get(decode(row[1])))) continue;
                createBoundary(diagramManager, diagrams, shapes, row);
            } else if ("N".equals(row[0])) {
                if ("SEQUENCE".equals(diagramTypes.get(decode(row[1])))) continue;
                createNode(diagramManager, diagrams, diagramTypes, shapes, row);
            } else if ("E".equals(row[0])) {
                if ("SEQUENCE".equals(diagramTypes.get(decode(row[1])))) continue;
                edges.add(row);
            } else {
                throw new IllegalArgumentException("Unknown exchange row: " + row[0]);
            }
        }

        for (String[] row : edges) {
            createEdge(diagramManager, diagrams, diagramTypes, shapes, row);
        }
        for (Map.Entry<String, String> entry : diagramTypes.entrySet()) {
            if ("SEQUENCE".equals(entry.getValue())) {
                createNativeSequence(diagramManager, (IInteractionDiagramUIModel) diagrams.get(entry.getKey()));
            }
        }

        if (!projectManager.saveProjectAs(output)) {
            throw new IllegalStateException("Visual Paradigm refused to save " + output);
        }
        System.out.println((append ? "Appended " : "Created ") + diagrams.size()
            + " native diagrams in " + output.getAbsolutePath());
    }

    private static void createNativeSequence(DiagramManager manager, IInteractionDiagramUIModel diagram) {
        IModelElementFactory factory = IModelElementFactory.instance();
        IFrame frame = diagram.getRootFrame(true);
        IModel owner = factory.createModel();
        owner.setName("OmniTrade end-to-end analysis interaction");
        owner.addSubDiagram(diagram);
        diagram.setShowSequenceNumbers(true);
        diagram.setShowActivations(true);
        diagram.setAutoExtendActivations(false);

        String[] names = {"Analyst", "React UI", "FastAPI", "PostgreSQL", "WorkflowRuntime", "Evidence Gateway", "Model Gateway", "Redis Events", "Report Service"};
        int[] xs = {40, 230, 420, 610, 800, 990, 1180, 1370, 1560};
        IActivation[] activations = new IActivation[names.length];
        IActivationUIModel[] activationShapes = new IActivationUIModel[names.length];
        for (int index = 0; index < names.length; index++) {
            IClass classifier = factory.createClass();
            classifier.setName(names[index]);
            IInteractionLifeLine lifeline = factory.createInteractionLifeLine();
            lifeline.setBaseClassifier(classifier);
            lifeline.setName(names[index].replace(" ", "").toLowerCase());
            frame.addInteractionLifeLine(lifeline);
            IInteractionLifeLineUIModel lifelineShape = (IInteractionLifeLineUIModel) manager.createDiagramElement(diagram, IInteractionDiagramUIModel.SHAPETYPE_INTERACTION_LIFE_LINE);
            lifelineShape.setModelElement(lifeline);
            lifelineShape.setBounds(xs[index], 55, 145, 2260);
            lifelineShape.setShowClassifier(true);
            lifelineShape.getElementFont().setValues("Segoe UI", true, false, 12, TEXT);

            IActivation activation = factory.createActivation();
            lifeline.addActivation(activation);
            IActivationUIModel activationShape = (IActivationUIModel) manager.createDiagramElement(diagram, IInteractionDiagramUIModel.SHAPETYPE_ACTIVATION);
            activationShape.setModelElement(activation);
            activationShape.setBounds(xs[index] + 67, 160, 12, 2110);
            activationShape.setBackground(Color.decode("#EAF2FF"));
            activationShape.setForeground(Color.decode("#5B7DB1"));
            activations[index] = activation;
            activationShapes[index] = activationShape;
        }

        Object[][] messages = {
            {0, 1, "Open Profile / New Analysis / Workflow Lab / Connections"},
            {1, 2, "GET profile, workflow versions, and session connection status"},
            {2, 3, "load UserProfile + immutable WorkflowVersion metadata"},
            {3, 2, "profile: analysis defaults + InvestorPolicy"},
            {2, 1, "prefill verified provider, quick/deep model, risk and report defaults"},
            {0, 1, "choose ticker/date/analysts/depth/budget; optionally override defaults"},
            {1, 2, "POST /runs with typed RunRequest"},
            {2, 3, "deep-copy RunConfiguration + InvestorPolicy + WorkflowVersion into QUEUED Run"},
            {2, 5, "recheck session-only data-provider connections"},
            {2, 6, "recheck session-only model/provider connection"},
            {2, 4, "start WorkflowTask(run_id, connections, trace_id)"},
            {4, 4, "validate graph, ports, loop bounds, side effects, and actual model-call budget"},
            {4, 3, "restore latest checkpoint or initialize NodeRuns"},
            {4, 4, "select deterministic ready set and cap bounded parallel wave"},
            {4, 5, "fetch real market/fundamental/news/macro/sentiment chains"},
            {5, 4, "normalized EvidenceSet or classified safe failure"},
            {4, 6, "execute selected specialists with evidence references"},
            {6, 4, "schema-validated AgentReports; retry invalid structured output"},
            {4, 6, "bounded Bull/Bear debate, proposal, and three risk perspectives"},
            {6, 4, "typed research/risk drafts; protected facts retained"},
            {4, 4, "deterministic risk gate applies deep-copied InvestorPolicy"},
            {4, 3, "checkpoint node outputs, loop state, and ordered durable events"},
            {4, 7, "publish low-latency progress event"},
            {0, 1, "optional Pause"},
            {1, 2, "POST /runs/{id}/pause"},
            {2, 4, "pause probe: PAUSING -> checkpoint -> PAUSED"},
            {0, 1, "Resume from Run History"},
            {1, 2, "POST /runs/{id}/resume"},
            {2, 5, "recheck data connections before resumed live work"},
            {2, 6, "recheck model connection before resumed live work"},
            {2, 4, "restore checkpoint; do not rerun completed nodes"},
            {4, 8, "Decision + outputs + lineage; confidence kept separate from research support"},
            {8, 3, "persist report metadata, JSON/HTML/PDF artifact, and SHA-256"},
            {2, 3, "combine durable DB events with Redis progress for Run History"},
            {2, 1, "report available only for SUCCEEDED or DEGRADED"}
        };
        int y = 205;
        for (int index = 0; index < messages.length; index++, y += 58) {
            int from = (Integer) messages[index][0];
            int to = (Integer) messages[index][1];
            addMessage(manager, diagram, activations[from], activations[to], activationShapes[from], activationShapes[to], index + 1, (String) messages[index][2], y);
        }
    }

    private static void addMessage(DiagramManager manager, IInteractionDiagramUIModel diagram,
                                   IActivation from, IActivation to,
                                   IActivationUIModel fromShape, IActivationUIModel toShape,
                                   int sequence, String label, int y) {
        IMessage message = IModelElementFactory.instance().createMessage();
        message.setName(label);
        message.setSequenceNumber(Integer.toString(sequence));
        message.setFromActivation(from);
        message.setToActivation(to);
        message.setType(from == to ? IMessage.TYPE_SELF_MESSAGE : IMessage.TYPE_MESSAGE);
        Point[] points;
        String shapeType;
        if (from == to) {
            points = new Point[] {new Point(fromShape.getX() + 12, y), new Point(fromShape.getX() + 80, y), new Point(fromShape.getX() + 80, y + 24), new Point(fromShape.getX() + 12, y + 24)};
            shapeType = IInteractionDiagramUIModel.SHAPETYPE_SELF_MESSAGE;
        } else {
            points = new Point[] {new Point(fromShape.getX() + 6, y), new Point(toShape.getX() + 6, y)};
            shapeType = IInteractionDiagramUIModel.SHAPETYPE_MESSAGE;
        }
        IMessageUIModel connector = (IMessageUIModel) manager.createConnector(diagram, shapeType, fromShape, toShape, points);
        connector.setModelElement(message);
        connector.setMetaModelElement(message);
        connector.setShowMessageName(IMessageUIModel.SHOW_MESSAGE_NAME_NO);
        connector.getElementFont().setValues("Segoe UI", false, false, 10, TEXT);
        connector.getLineModel().setWeight(1.4f, true);
        connector.setForeground(Color.decode("#475467"));
        createSequenceLabel(manager, diagram, sequence + "  " + label, fromShape, toShape, y);
    }

    private static void createSequenceLabel(DiagramManager manager, IInteractionDiagramUIModel diagram,
                                            String label, IShapeUIModel fromShape, IShapeUIModel toShape, int y) {
        int center = (fromShape.getX() + toShape.getX()) / 2 + 6;
        int width = Math.max(180, Math.min(520, label.length() * 6 + 20));
        IShapeUIModel annotation = (IShapeUIModel) manager.createDiagramElement(diagram, IInteractionDiagramUIModel.SHAPETYPE_GENERIC_SHAPE);
        setName(annotation, label);
        annotation.setBounds(center - width / 2, y - 28, width, 24);
        annotation.setBackground(Color.WHITE);
        annotation.setForeground(Color.decode("#FFFFFF"));
        annotation.getElementFont().setValues("Segoe UI", false, false, 9, TEXT);
        annotation.setModelElementNameAlignment(IDiagramElement.MODEL_ELEMENT_NAME_ALIGNMENT_ALIGN_MIDDLE);
        annotation.setRequestResetCaption(true);
        annotation.setRequestResetCaptionSize(true);
        annotation.setRequestResetCaptionFitWidth(true);
        annotation.bringToFront();
    }

    private static void createBoundary(DiagramManager manager, Map<String, IDiagramUIModel> diagrams,
                                       Map<String, Map<String, IDiagramElement>> shapes, String[] row) {
        String diagramId = decode(row[1]);
        String key = decode(row[2]);
        String title = decode(row[3]);
        String diagramType = diagrams.get(diagramId).getType();
        IDiagramUIModel diagram = diagrams.get(diagramId);
        IShapeUIModel shape;
        if (DiagramManager.DIAGRAM_TYPE_USE_CASE_DIAGRAM.equals(diagramType)) {
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, IUseCaseDiagramUIModel.SHAPETYPE_SYSTEM);
        } else if (DiagramManager.DIAGRAM_TYPE_COMPOSITE_STRUCTURE_DIAGRAM.equals(diagramType)) {
            IClass classifier = IModelElementFactory.instance().createClass();
            classifier.setName(title);
            classifier.setDocumentation("Composite structure boundary for " + title);
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, classifier);
        } else if (DiagramManager.DIAGRAM_TYPE_TIMING_DIAGRAM.equals(diagramType)) {
            ITimingFrame frame = IModelElementFactory.instance().createTimingFrame();
            frame.setName(title);
            // A timing diagram is rendered from one frame whose owned model
            // contains time units, lifelines, states, and time instances.  VP
            // does not support lifelines or state conditions as top-level
            // timing-diagram shapes.
            for (int index = 0; index < 60; index++) {
                ITimeUnit unit = IModelElementFactory.instance().createTimeUnit();
                unit.setName(index % 10 == 0 ? "T" + (index / 10) : "");
                frame.addTimeUnit(unit);
            }
            ITimingFrameUIModel frameShape = (ITimingFrameUIModel)
                manager.createDiagramElement(diagram, frame);
            frameShape.setViewMode(ITimingFrameUIModel.VM_COMPACT);
            frameShape.setLifeLineWidth(190);
            frameShape.setStateConditionWidth(145);
            shape = frameShape;
        } else if (DiagramManager.DIAGRAM_TYPE_DEPLOYMENT.equals(diagramType)) {
            INode node = IModelElementFactory.instance().createNode();
            node.setName(title);
            node.setDocumentation("Deployment node boundary: " + title);
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, node);
        } else if (DiagramManager.DIAGRAM_TYPE_COMPONENT_DIAGRAM.equals(diagramType)) {
            IPackage subsystem = IModelElementFactory.instance().createPackage();
            subsystem.setName(title);
            subsystem.setDocumentation("Component subsystem boundary: " + title);
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, subsystem);
        } else if (DiagramManager.DIAGRAM_TYPE_PACKAGE_DIAGRAM.equals(diagramType)) {
            IPackage pkg = IModelElementFactory.instance().createPackage();
            pkg.setName(title);
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, pkg);
        } else if (DiagramManager.DIAGRAM_TYPE_CLASS_DIAGRAM.equals(diagramType)) {
            IPackage pkg = IModelElementFactory.instance().createPackage();
            pkg.setName(title);
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, pkg);
        } else if (DiagramManager.DIAGRAM_TYPE_ACTIVITY_DIAGRAM.equals(diagramType)) {
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, IActivityDiagramUIModel.SHAPETYPE_STRUCTURED_ACTIVITY_NODE);
        } else if (DiagramManager.DIAGRAM_TYPE_STATE_DIAGRAM.equals(diagramType)) {
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, IStateDiagramUIModel.SHAPETYPE_STATE2);
            if (shape instanceof IStateUIModel) {
                ((IStateUIModel) shape).setActionCompartmentVisible(false);
                ((IStateUIModel) shape).setInternalTransitionCompartmentVisible(false);
                ((IStateUIModel) shape).setDeferrableEventVisible(false);
            }
        } else {
            IPackage section = IModelElementFactory.instance().createPackage();
            section.setName(title);
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, section);
        }
        setName(shape, title);
        shape.setBounds(number(row[4]), number(row[5]), number(row[6]), number(row[7]));
        if (shape instanceof ITimingFrameUIModel) {
            ITimingFrameUIModel timingShape = (ITimingFrameUIModel) shape;
            timingShape.setViewMode(ITimingFrameUIModel.VM_COMPACT);
            timingShape.setLifeLineWidth(190);
            timingShape.setStateConditionWidth(145);
        }
        shape.setBackground(color(row[8]));
        shape.setForeground(color(row[9]));
        shape.getFillColor().setTransparency(88, true);
        shape.setModelElementNameAlignment(IDiagramElement.MODEL_ELEMENT_NAME_ALIGNMENT_ALIGN_TOP_LEFT);
        shape.getElementFont().setValues("Segoe UI", true, false, 15, TEXT);
        shape.getLineModel().setWeight(1.6f, true);
        shape.setRequestResetCaption(true);
        shape.setRequestResetCaptionSize(true);
        shape.resetCaption();
        shape.getCaptionUIModel().setSide(com.vp.plugin.diagram.ICaptionUIModel.SIDE_INSIDENORTH);
        shape.getCaptionUIModel().setBounds(shape.getX() + 18, shape.getY() + 8,
            Math.max(120, shape.getWidth() - 36), 30);
        shape.sendToBack();
        shapes.get(diagramId).put(key, shape);
        attachToContainingBoundary(shapes.get(diagramId), shape);
    }

    private static void createNode(DiagramManager manager, Map<String, IDiagramUIModel> diagrams,
                                   Map<String, String> diagramTypes,
                                   Map<String, Map<String, IDiagramElement>> shapes, String[] row) {
        String diagramId = decode(row[1]);
        String key = decode(row[2]);
        String stereotype = decode(row[3]);
        String title = decode(row[4]);
        String details = decode(row[5]);
        String type = diagramTypes.get(diagramId);
        IDiagramUIModel diagram = diagrams.get(diagramId);
        if ("TIMING".equals(type)
            && ("lifeline".equals(stereotype) || "timingstate".equals(stereotype))) {
            createTimingElement(diagramId, key, stereotype, title, details,
                shapes.get(diagramId));
            return;
        }
        IShapeUIModel shape = createSemanticNode(manager, diagram, type, diagramId, key,
            stereotype, title, details, shapes.get(diagramId));
        shape.setBounds(number(row[6]), number(row[7]), number(row[8]), number(row[9]));
        shape.setBackground(color(row[10]));
        shape.setForeground(color(row[11]));
        if (!("actor".equals(stereotype))
            && !(shape instanceof IClassUIModel)
            && !(shape instanceof IComponentUIModel)
            && !(shape instanceof IInstanceSpecificationUIModel)) {
            shape.setModelElementNameAlignment(IDiagramElement.MODEL_ELEMENT_NAME_ALIGNMENT_ALIGN_MIDDLE);
        }
        shape.setConnectionPointType(IShapeUIModel.CONNECTION_POINT_TYPE_ROUNDTHESHAPE);
        shape.getElementFont().setValues("Segoe UI", false, false,
            ("note".equals(stereotype) || "constraint".equals(stereotype)) ? 12 : 13, TEXT);
        shape.getLineModel().setWeight(1.7f, true);
        shape.setRequestResetCaption(true);
        shape.setRequestResetCaptionSize(true);
        shape.setRequestResetCaptionFitWidth(true);
        shape.resetCaption();
        if ("COMPOSITE".equals(type) && "port".equals(stereotype)) {
            shape.getCaptionUIModel().setSide(com.vp.plugin.diagram.ICaptionUIModel.SIDE_FREEMOVE);
            int captionX = shape.getX() < 1000 ? shape.getX() - 10 : shape.getX() - 310;
            shape.getCaptionUIModel().setBounds(captionX, shape.getY() + shape.getHeight() + 8, 300, 86);
        } else if (!(shape instanceof IClassUIModel)
            && !(shape instanceof IComponentUIModel)
            && !(shape instanceof IInstanceSpecificationUIModel)) {
            shape.getCaptionUIModel().setBounds(shape.getX() + 8, shape.getY() + 6,
                Math.max(30, shape.getWidth() - 16), Math.max(22, shape.getHeight() - 12));
        }
        shapes.get(diagramId).put(key, shape);
        if ("COMPOSITE".equals(type) && "port".equals(stereotype)) {
            attachPortToBoundary(shapes.get(diagramId), shape);
        } else {
            attachToContainingBoundary(shapes.get(diagramId), shape);
        }
    }

    private static IShapeUIModel createSemanticNode(DiagramManager manager, IDiagramUIModel diagram,
                                                     String type, String diagramId, String key,
                                                     String stereotype,
                                                     String title, String details,
                                                     Map<String, IDiagramElement> diagramShapes) {
        IModelElementFactory factory = IModelElementFactory.instance();
        IShapeUIModel shape;

        if ("note".equals(stereotype) || "constraint".equals(stereotype)) {
            INOTE note = factory.createNOTE();
            note.setName(joinCaption(title, details));
            // Native notes render their documentation body.  Include the
            // concise heading in that body so exported review images keep the
            // rationale visible instead of showing an anonymous paragraph.
            note.setDocumentation(joinCaption(title, details));
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, note);
            return shape;
        }

        if ("CLASS".equals(type)) {
            IClass model = factory.createClass();
            model.setName(title);
            model.setDocumentation(details);
            CLASSIFIERS.putIfAbsent(title, model);
            for (String line : detailLines(details, 5)) {
                IAttribute attribute = factory.createAttribute();
                attribute.setName(line);
                attribute.setVisibility(IAttribute.VISIBILITY_PRIVATE);
                model.addAttribute(attribute);
            }
            IClassUIModel classShape = (IClassUIModel) manager.createDiagramElement(diagram, model);
            classShape.setShowAttributeType(IClassUIModel.ATTR_SHOW_TYPE_ALL);
            classShape.setShowOperationType(IClassUIModel.OP_SHOW_TYPE_NONE);
            classShape.setShowEmptyCompartments(2);
            classShape.setWrapMembers(true);
            return classShape;
        }

        if ("COMPONENT".equals(type) || "DEPLOYMENT".equals(type)) {
            IComponent component = factory.createComponent();
            component.setName(title);
            component.setDocumentation(details);
            for (String line : detailLines(details, 3)) {
                IOperation operation = factory.createOperation();
                operation.setName(line);
                operation.setVisibility(IOperation.VISIBILITY_PRIVATE);
                component.addOperation(operation);
            }
            IComponentUIModel componentShape = (IComponentUIModel) manager.createDiagramElement(diagram, component);
            componentShape.setShowAttributesMode(IComponentUIModel.SHOW_ATTRIBUTES_MODE_HIDE_ALL);
            componentShape.setShowOperationsMode(details.isBlank()
                ? IComponentUIModel.SHOW_OPERATIONS_MODE_HIDE_ALL
                : IComponentUIModel.SHOW_OPERATIONS_MODE_SHOW_ALL);
            componentShape.setShowOption(IComponentUIModel.SHOW_COMPONENT_OPTION_ICON);
            return componentShape;
        }

        if ("OVERVIEW".equals(type) && "component".equals(stereotype)) {
            IComponent component = factory.createComponent();
            component.setName(title);
            component.setDocumentation(details);
            for (String line : detailLines(details, 3)) {
                IOperation operation = component.createOperation();
                operation.setName(line);
                operation.setVisibility(IOperation.VISIBILITY_PRIVATE);
            }
            IComponentUIModel componentShape = (IComponentUIModel)
                manager.createDiagramElement(diagram, component);
            componentShape.setShowAttributesMode(IComponentUIModel.SHOW_ATTRIBUTES_MODE_HIDE_ALL);
            componentShape.setShowOperationsMode(IComponentUIModel.SHOW_OPERATIONS_MODE_SHOW_ALL);
            componentShape.setShowOption(IComponentUIModel.SHOW_COMPONENT_OPTION_ICON);
            return componentShape;
        }

        if ("PACKAGE".equals(type)) {
            IPackage pkg = factory.createPackage();
            pkg.setName(title);
            pkg.setDocumentation(details);
            return (IShapeUIModel) manager.createDiagramElement(diagram, pkg);
        }

        if ("COMMUNICATION".equals(type) && "lifeline".equals(stereotype)) {
            IClass classifier = factory.createClass();
            String classifierTitle = title.replaceFirst("^:", "");
            classifier.setName(joinCaption(classifierTitle, details));
            classifier.setDocumentation(details);
            IInteractionLifeLine lifeline = factory.createInteractionLifeLine();
            lifeline.setBaseClassifier(classifier);
            String objectName = classifierTitle.replaceAll("[^A-Za-z0-9]", "").toLowerCase();
            lifeline.setName(objectName.isBlank() ? "participant" : objectName);
            lifeline.setDocumentation(details);
            return (IShapeUIModel) manager.createDiagramElement(diagram, lifeline);
        }

        if ("INTERACTION_OVERVIEW".equals(type)) {
            if ("start".equals(stereotype)) {
                IInitialNode start = factory.createInitialNode();
                start.setName(title);
                return (IShapeUIModel) manager.createDiagramElement(diagram, start);
            }
            if ("end".equals(stereotype)) {
                IActivityFinalNode end = factory.createActivityFinalNode();
                end.setName(title);
                return (IShapeUIModel) manager.createDiagramElement(diagram, end);
            }
            if ("decision".equals(stereotype)) {
                IDecisionNode decision = factory.createDecisionNode();
                decision.setName(title);
                decision.setDocumentation(details);
                return (IShapeUIModel) manager.createDiagramElement(diagram, decision);
            }
            if ("interaction".equals(stereotype)) {
                IInteractionOccurrence occurrence = factory.createInteractionOccurrence();
                IFrame referencedFrame = factory.createFrame();
                referencedFrame.setName(joinCaption(title, details));
                referencedFrame.setDocumentation(details);
                occurrence.setRefersTo(referencedFrame);
                occurrence.setName(title);
                occurrence.setDocumentation(details);
                IInteractionOccurrenceUIModel occurrenceShape = (IInteractionOccurrenceUIModel)
                    manager.createDiagramElement(diagram, occurrence);
                occurrenceShape.setShowPreview(false);
                return occurrenceShape;
            }
        }

        if ("OBJECT".equals(type) && "object".equals(stereotype)) {
            String raw = title.trim();
            String instanceName = "";
            String classifierToken = raw;
            if (raw.startsWith(":")) {
                classifierToken = raw.substring(1).trim();
            } else if (raw.contains(":")) {
                String[] objectType = raw.split(":", 2);
                instanceName = objectType[0].trim();
                classifierToken = objectType[1].trim();
            }
            String classifierName = classifierToken.replaceFirst("\\[.*$", "");
            if (instanceName.isBlank() && classifierToken.contains("[")) {
                instanceName = classifierToken.replaceFirst("^[^\\[]+\\[", "")
                    .replaceFirst("\\]$", "");
            }
            IClass classifier = CLASSIFIERS.get(classifierName);
            if (classifier == null) {
                classifier = factory.createClass();
                classifier.setName(classifierName);
                CLASSIFIERS.put(classifierName, classifier);
            }
            IInstanceSpecification instance = factory.createInstanceSpecification();
            // Visual Paradigm CE keeps the slot compartment collapsed in some
            // headless exports.  Keep real UML slots in the model and repeat
            // their compact values in the instance caption so the exported
            // review artifact never becomes an empty object box.
            instance.setName(joinCaption(instanceName, details));
            instance.setDocumentation(details);
            instance.addClassifier(classifier);
            for (String line : detailLines(details, 6)) {
                String[] pair = line.split("\\s*=\\s*", 2);
                IAttribute feature = classifier.createAttribute();
                feature.setName(pair[0].trim());
                feature.setType("String");
                ISlot slot = factory.createSlot();
                slot.setFeature(feature);
                ICompositeValueSpecification value = factory.createCompositeValueSpecification();
                value.setValue(pair.length == 2 ? pair[1].trim() : "true");
                slot.addValue(value);
                instance.addSlot(slot);
            }
            IInstanceSpecificationUIModel objectShape = (IInstanceSpecificationUIModel)
                manager.createDiagramElement(diagram, instance);
            objectShape.setShowSlotsMode(IInstanceSpecificationUIModel.SHOW_SLOTS_MODE_SHOW_ALL);
            return objectShape;
        }

        if ("COMPOSITE".equals(type)) {
            try {
                IClass structuredClassifier = compositeOwner(diagramShapes);
                if ("port".equals(stereotype)) {
                    IPort port = factory.createPort();
                    port.setName(title);
                    port.setDocumentation(details);
                    port.setType("WorkflowRuntimePort");
                    if (structuredClassifier != null) structuredClassifier.addPort(port);
                    return (IShapeUIModel) manager.createDiagramElement(diagram, port);
                }
                String[] pair = title.split(":", 2);
                String partName = pair[0].trim();
                String classifierName = pair.length == 2 ? pair[1].trim() : title.trim();
                IClass classifier = factory.createClass();
                classifier.setName(classifierName);
                IAttribute part = factory.createAttribute();
                part.setName(joinCaption(partName, details));
                part.setType(classifier);
                part.setDocumentation(details);
                if (structuredClassifier != null) structuredClassifier.addAttribute(part);
                return (IShapeUIModel) manager.createDiagramElement(diagram, part);
            } catch (RuntimeException unsupportedCompositePart) {
                IShapeUIModel fallback = (IShapeUIModel) manager.createDiagramElement(
                    diagram, IOverviewDiagramUIModel.SHAPETYPE_GENERIC_SHAPE);
                fallback.setPresentationOption(IShapeUIModel.PRESENTATION_OPTION_PRIMITIVE);
                fallback.setPrimitiveShapeType(IShapeUIModel.PRIMITIVE_SHAPE_TYPE_ROUNDED_RECTANGLE);
                setName(fallback, title);
                return fallback;
            }
        }

        String shapeType = shapeType(type, stereotype);
        try {
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, shapeType);
            if (IOverviewDiagramUIModel.SHAPETYPE_GENERIC_SHAPE.equals(shapeType)) {
                shape.setPresentationOption(IShapeUIModel.PRESENTATION_OPTION_PRIMITIVE);
                shape.setPrimitiveShapeType(IShapeUIModel.PRIMITIVE_SHAPE_TYPE_ROUNDED_RECTANGLE);
            }
        } catch (RuntimeException unsupported) {
            shape = (IShapeUIModel) manager.createDiagramElement(diagram, IOverviewDiagramUIModel.SHAPETYPE_GENERIC_SHAPE);
            shape.setPresentationOption(IShapeUIModel.PRESENTATION_OPTION_PRIMITIVE);
            shape.setPrimitiveShapeType(IShapeUIModel.PRIMITIVE_SHAPE_TYPE_ROUNDED_RECTANGLE);
        }

        // Actor, use-case, state, decision and interaction names remain concise.
        // Their implementation details are retained in model documentation.
        boolean concise = "USE_CASE".equals(type) || "STATE".equals(type)
            || "COMMUNICATION".equals(type) || "INTERACTION_OVERVIEW".equals(type)
            || "COMPOSITE".equals(type);
        setName(shape, concise ? title : joinCaption(title, details));
        IModelElement model = shape.getModelElement() != null ? shape.getModelElement() : shape.getMetaModelElement();
        if (model != null) model.setDocumentation(details);
        if (shape instanceof IStateUIModel) {
            IStateUIModel state = (IStateUIModel) shape;
            state.setActionCompartmentVisible(false);
            state.setInternalTransitionCompartmentVisible(false);
            state.setDeferrableEventVisible(false);
        }
        return shape;
    }

    private static IClass compositeOwner(Map<String, IDiagramElement> diagramShapes) {
        if (diagramShapes == null) return null;
        for (Map.Entry<String, IDiagramElement> entry : diagramShapes.entrySet()) {
            if (!entry.getKey().startsWith("boundary_")) continue;
            IModelElement model = entry.getValue().getModelElement() != null
                ? entry.getValue().getModelElement()
                : entry.getValue().getMetaModelElement();
            if (model instanceof IClass) return (IClass) model;
        }
        return null;
    }

    private static ITimingFrame timingFrame(Map<String, IDiagramElement> diagramShapes) {
        if (diagramShapes == null) return null;
        for (Map.Entry<String, IDiagramElement> entry : diagramShapes.entrySet()) {
            if (!entry.getKey().startsWith("boundary_")) continue;
            IModelElement model = entry.getValue().getModelElement() != null
                ? entry.getValue().getModelElement()
                : entry.getValue().getMetaModelElement();
            if (model instanceof ITimingFrame) return (ITimingFrame) model;
        }
        return null;
    }

    private static void createTimingElement(String diagramId, String key, String stereotype,
                                            String title, String details,
                                            Map<String, IDiagramElement> diagramShapes) {
        IModelElementFactory factory = IModelElementFactory.instance();
        ITimingFrame frame = timingFrame(diagramShapes);
        if (frame == null) {
            throw new IllegalStateException("Timing frame missing for " + diagramId);
        }
        if ("lifeline".equals(stereotype)) {
            ILifeLine lifeline = factory.createLifeLine();
            lifeline.setName(title);
            lifeline.setDocumentation(details);
            frame.addLifeLine(lifeline);
            String lane = key.startsWith("label_") ? key.substring(6) : key;
            TIMING_LIFELINES.put(diagramId + ":" + lane, lifeline);
            return;
        }

        String lane = key.replaceFirst("_[0-9]+$", "");
        ILifeLine lifeline = TIMING_LIFELINES.get(diagramId + ":" + lane);
        if (lifeline == null) {
            throw new IllegalStateException("Timing lifeline missing for " + diagramId + ":" + lane);
        }
        IStateCondition condition = factory.createStateCondition();
        condition.setName(title);
        condition.setDocumentation(details);
        lifeline.addStateCondition(condition);

        int stateIndex = Integer.parseInt(key.replaceFirst("^.*_([0-9]+)$", "$1"));
        int firstUnit = stateIndex * 10;
        for (int index = firstUnit; index <= firstUnit + 9 && index < frame.timeUnitCount(); index++) {
            ITimeInstance instance = factory.createTimeInstance();
            instance.setStateCondition(condition);
            instance.setTimeUnit(frame.getTimeUnitByIndex(index));
            lifeline.addTimeInstance(instance);
        }
    }

    private static String joinCaption(String title, String details) {
        return details == null || details.isBlank() ? title : title + "\n" + details;
    }

    private static String[] detailLines(String details, int maximum) {
        if (details == null || details.isBlank()) return new String[0];
        String[] all = details.split("\\n");
        int count = Math.min(maximum, all.length);
        String[] result = new String[count];
        System.arraycopy(all, 0, result, 0, count);
        return result;
    }

    private static void attachToContainingBoundary(Map<String, IDiagramElement> diagramShapes,
                                                    IShapeUIModel child) {
        IShapeUIModel selected = null;
        long selectedArea = Long.MAX_VALUE;
        int centerX = child.getX() + child.getWidth() / 2;
        int centerY = child.getY() + child.getHeight() / 2;
        for (Map.Entry<String, IDiagramElement> entry : diagramShapes.entrySet()) {
            if (!entry.getKey().startsWith("boundary_")) continue;
            if (!(entry.getValue() instanceof IShapeUIModel)) continue;
            IShapeUIModel boundary = (IShapeUIModel) entry.getValue();
            if (boundary == child) continue;
            if (centerX > boundary.getX() + 12 && centerX < boundary.getX() + boundary.getWidth() - 12
                && centerY > boundary.getY() + 38 && centerY < boundary.getY() + boundary.getHeight() - 12) {
                long area = (long) boundary.getWidth() * boundary.getHeight();
                if (area < selectedArea) {
                    selected = boundary;
                    selectedArea = area;
                }
            }
        }
        if (selected != null) selected.addChild(child);
    }

    private static void attachPortToBoundary(Map<String, IDiagramElement> diagramShapes,
                                             IShapeUIModel port) {
        IShapeUIModel selected = null;
        long selectedArea = Long.MAX_VALUE;
        int centerX = port.getX() + port.getWidth() / 2;
        int centerY = port.getY() + port.getHeight() / 2;
        for (Map.Entry<String, IDiagramElement> entry : diagramShapes.entrySet()) {
            if (!entry.getKey().startsWith("boundary_")) continue;
            if (!(entry.getValue() instanceof IShapeUIModel)) continue;
            IShapeUIModel boundary = (IShapeUIModel) entry.getValue();
            int leftDistance = Math.abs(centerX - boundary.getX());
            int rightDistance = Math.abs(centerX - (boundary.getX() + boundary.getWidth()));
            boolean onVerticalEdge = Math.min(leftDistance, rightDistance) <= 30;
            boolean withinHeight = centerY > boundary.getY() + 34
                && centerY < boundary.getY() + boundary.getHeight() - 10;
            if (onVerticalEdge && withinHeight) {
                long area = (long) boundary.getWidth() * boundary.getHeight();
                if (area < selectedArea) {
                    selected = boundary;
                    selectedArea = area;
                }
            }
        }
        if (selected != null) selected.addChild(port);
    }

    private static void createEdge(DiagramManager manager, Map<String, IDiagramUIModel> diagrams,
                                   Map<String, String> diagramTypes,
                                   Map<String, Map<String, IDiagramElement>> shapes, String[] row) {
        String diagramId = decode(row[1]);
        String label = decode(row[3]);
        Point[] points = points(decode(row[4]));
        Map<String, IDiagramElement> diagramShapes = shapes.get(diagramId);
        String diagramType = diagramTypes.get(diagramId);
        // Timing-state continuity is rendered by Visual Paradigm from adjacent
        // time instances in the native timing frame.  Importing the authored
        // helper routes as separate connectors would duplicate that notation.
        if ("TIMING".equals(diagramType)) return;
        IDiagramElement from = endpoint(diagramShapes, points[0], diagramType);
        IDiagramElement to = endpoint(diagramShapes, points[points.length - 1], diagramType);
        if (from == null || to == null) {
            throw new IllegalStateException("Cannot resolve connector endpoints in " + diagramId + ": " + label);
        }
        if ("COMMUNICATION".equals(diagramType)) {
            createCommunicationMessage(manager, (ICommunicationDiagramUIModel) diagrams.get(diagramId),
                from, to, points, label, row);
            return;
        }
        String connectorType = connectorType(diagramType, label, "1".equals(row[6]));
        IDiagramElement connector;
        try {
            connector = createModelConnector(manager, diagrams.get(diagramId), diagramType,
                connectorType, from, to, points, label);
        } catch (RuntimeException unsupported) {
            connector = manager.createConnector(diagrams.get(diagramId), IOverviewDiagramUIModel.SHAPETYPE_GENERIC_CONNECTOR, from, to, points);
        }
        connector.setForeground(color(row[5]));
        if (connector instanceof IConnectorUIModel) {
            IConnectorUIModel routed = (IConnectorUIModel) connector;
            routed.setConnectorStyle(points.length <= 2 ? IConnectorUIModel.CS_OBLIQUE : IConnectorUIModel.CS_RECTI_LINEAR);
            routed.setConnectorLineJumps(IConnectorUIModel.CLJ_GAP);
            routed.setRequestRebuild(false);
        }
        connector.getLineModel().setWeight(1.8f, true);
        String visibleLabel = label;
        if ("USE_CASE".equals(diagramType)
            && !label.contains("include") && !label.contains("extend")) {
            // UML actor associations are intentionally unlabelled.  Earlier
            // prose labels collided with actor names and added no semantics.
            visibleLabel = "";
        }
        if ("COMPONENT".equals(diagramType) || "PACKAGE".equals(diagramType)
            || "DEPLOYMENT".equals(diagramType)) {
            // Dense architecture views reserve connectors for topology.  Their
            // contracts are expressed by native operations/documentation, not
            // by long captions laid across subsystem boundaries.
            visibleLabel = "";
        }
        if (!visibleLabel.isBlank()) {
            setName(connector, visibleLabel);
            positionConnectorCaption(connector, visibleLabel, row);
        } else if (connector instanceof IConnectorUIModel) {
            ((IConnectorUIModel) connector).setShowConnectorName(2);
        }
    }

    private static IDiagramElement createModelConnector(DiagramManager manager, IDiagramUIModel diagram,
                                                        String diagramType, String connectorType,
                                                        IDiagramElement from, IDiagramElement to,
                                                        Point[] points, String label) {
        IModelElement fromModel = from.getModelElement() != null ? from.getModelElement() : from.getMetaModelElement();
        IModelElement toModel = to.getModelElement() != null ? to.getModelElement() : to.getMetaModelElement();
        IModelElementFactory factory = IModelElementFactory.instance();
        if (fromModel != null && toModel != null) {
            if ("STATE".equals(diagramType)) {
                ITransition2 transition = factory.createTransition2();
                transition.setFrom(fromModel);
                transition.setTo(toModel);
                transition.setName(label);
                IDiagramElement transitionShape = manager.createConnector(
                    diagram, transition, from, to, points);
                if (label != null && !label.isBlank()) {
                    IOperation operation = factory.createOperation();
                    operation.setName(label);
                    ICallTrigger trigger = factory.createCallTrigger();
                    trigger.setName(label);
                    trigger.setOperation(operation);
                    transition.addTrigger(trigger);
                }
                transitionShape.setRequestResetCaption(true);
                return transitionShape;
            }
            if ("ACTIVITY".equals(diagramType)) {
                IControlFlow flow = factory.createControlFlow();
                flow.setFrom(fromModel);
                flow.setTo(toModel);
                flow.setName(label);
                return manager.createConnector(diagram, flow, from, to, points);
            }
            if ("OBJECT".equals(diagramType)
                && fromModel instanceof IInstanceSpecification
                && toModel instanceof IInstanceSpecification) {
                IInstanceSpecification fromInstance = (IInstanceSpecification) fromModel;
                IInstanceSpecification toInstance = (IInstanceSpecification) toModel;
                IAssociation association = factory.createAssociation();
                association.setName(label);
                if (fromInstance.classifierCount() > 0 && toInstance.classifierCount() > 0) {
                    association.setFrom(fromInstance.getClassifierByIndex(0));
                    association.setTo(toInstance.getClassifierByIndex(0));
                }
                ILink link = factory.createLink();
                link.setFrom(fromInstance);
                link.setTo(toInstance);
                link.setName(label);
                link.addClassifier(association);
                return manager.createConnector(diagram, link, from, to, points);
            }
            if ("CLASS".equals(diagramType)) {
                IAssociation association = factory.createAssociation();
                association.setFrom(fromModel);
                association.setTo(toModel);
                association.setName(label);
                return manager.createConnector(diagram, association, from, to, points);
            }
            if ("PACKAGE".equals(diagramType) || "COMPONENT".equals(diagramType)
                || "DEPLOYMENT".equals(diagramType)) {
                IDependency dependency = factory.createDependency();
                dependency.setFrom(fromModel);
                dependency.setTo(toModel);
                dependency.setName(label);
                return manager.createConnector(diagram, dependency, from, to, points);
            }
        }
        return manager.createConnector(diagram, connectorType, from, to, points);
    }

    private static void positionConnectorCaption(IDiagramElement connector, String label, String[] row) {
        if (row.length < 10) {
            return;
        }
        int x = number(row[8]);
        int y = number(row[9]);
        String[] lines = label.split("\\n", -1);
        int longest = 0;
        for (String line : lines) {
            longest = Math.max(longest, line.length());
        }
        int width = Math.max(90, Math.min(300, longest * 7 + 18));
        int height = Math.max(26, Math.max(lines.length, (longest / 38) + 1) * 17 + 8);
        connector.getElementFont().setValues("Segoe UI", false, false, 10, TEXT);
        connector.setRequestResetCaption(false);
        connector.getCaptionUIModel().setSide(com.vp.plugin.diagram.ICaptionUIModel.SIDE_FREEMOVE);
        connector.getCaptionUIModel().setBounds(x - width / 2, y - height / 2, width, height);
        if (connector instanceof IConnectorUIModel) {
            IConnectorUIModel routed = (IConnectorUIModel) connector;
            routed.setShowConnectorName(1);
            routed.setPaintThroughLabel(2);
        }
    }

    private static void createCommunicationMessage(DiagramManager manager,
                                                    ICommunicationDiagramUIModel diagram,
                                                    IDiagramElement from, IDiagramElement to,
                                                    Point[] points, String label, String[] row) {
        IInteractionLifeLine fromModel = (IInteractionLifeLine) from.getModelElement();
        IInteractionLifeLine toModel = (IInteractionLifeLine) to.getModelElement();
        IModelElementFactory factory = IModelElementFactory.instance();
        IInteractionLifeLineLink link = factory.createInteractionLifeLineLink();
        link.setFrom(fromModel);
        link.setTo(toModel);
        link.setName(label);

        IMessage message = factory.createMessage();
        String sequence = "";
        String name = label;
        int split = label.indexOf(' ');
        if (split > 0 && label.substring(0, split).matches("[0-9.]+")) {
            sequence = label.substring(0, split);
            name = label.substring(split + 1);
        }
        message.setName(name);
        message.setSequenceNumber(sequence);
        message.setFrom(fromModel);
        message.setTo(toModel);
        link.addMessage(message);

        IConnectorUIModel linkShape = (IConnectorUIModel) manager.createConnector(diagram, link, from, to, points);
        linkShape.setConnectorStyle(points.length <= 2 ? IConnectorUIModel.CS_OBLIQUE : IConnectorUIModel.CS_RECTI_LINEAR);
        linkShape.setConnectorLineJumps(IConnectorUIModel.CLJ_GAP);
        linkShape.setRequestRebuild(false);
        linkShape.setForeground(color(row[5]));
        linkShape.getLineModel().setWeight(1.6f, true);
        // Keep the message as a native child of the UML link model.  The VP
        // headless renderer always draws a separate communication-message
        // arrow horizontally, which becomes detached on vertical or routed
        // object links.  A positioned link caption presents the same numbered
        // message without those misleading floating arrowheads.
        setName(linkShape, label);
        positionConnectorCaption(linkShape, label, row);
        int x = number(row[8]);
        int y = number(row[9]);
        int width = Math.max(180, Math.min(420, label.length() * 7 + 28));
        INOTE messageLabel = factory.createNOTE();
        messageLabel.setName(label);
        messageLabel.setDocumentation(label);
        IShapeUIModel annotation = (IShapeUIModel) manager.createDiagramElement(diagram, messageLabel);
        annotation.setBounds(x - width / 2, y - 17, width, 34);
        annotation.setBackground(Color.WHITE);
        annotation.setForeground(Color.WHITE);
        annotation.getElementFont().setValues("Segoe UI", false, false, 10, TEXT);
        annotation.setModelElementNameAlignment(IDiagramElement.MODEL_ELEMENT_NAME_ALIGNMENT_ALIGN_MIDDLE);
        annotation.setRequestResetCaption(true);
        annotation.setRequestResetCaptionSize(true);
        annotation.setRequestResetCaptionFitWidth(true);
        annotation.resetCaption();
        annotation.bringToFront();
    }

    private static IDiagramElement endpoint(Map<String, IDiagramElement> shapes, Point point, String diagramType) {
        IDiagramElement best = null;
        double distance = Double.MAX_VALUE;
        for (Map.Entry<String, IDiagramElement> entry : shapes.entrySet()) {
            if (entry.getKey().startsWith("boundary_")) {
                continue;
            }
            IDiagramElement element = entry.getValue();
            if (!(element instanceof IShapeUIModel)) {
                continue;
            }
            IShapeUIModel shape = (IShapeUIModel) element;
            int left = shape.getX();
            int right = shape.getX() + shape.getWidth();
            int top = shape.getY();
            int bottom = shape.getY() + shape.getHeight();
            int dx = point.x < left ? left - point.x : point.x > right ? point.x - right : 0;
            int dy = point.y < top ? top - point.y : point.y > bottom ? point.y - bottom : 0;
            double current = Math.hypot(dx, dy);
            if (current < distance) {
                distance = current;
                best = shape;
            }
        }
        if (distance <= 3.0) {
            return best;
        }
        if ("SEQUENCE".equals(diagramType)) {
            best = null;
            distance = Double.MAX_VALUE;
            for (Map.Entry<String, IDiagramElement> entry : shapes.entrySet()) {
                if (entry.getKey().startsWith("boundary_")) continue;
                IDiagramElement element = entry.getValue();
                if (!(element instanceof IShapeUIModel)) continue;
                IShapeUIModel shape = (IShapeUIModel) element;
                int left = shape.getX();
                int right = shape.getX() + shape.getWidth();
                double current = point.x < left ? left - point.x : point.x > right ? point.x - right : 0;
                if (current < distance) {
                    distance = current;
                    best = shape;
                }
            }
            return best;
        }
        return null;
    }

    private static String diagramType(String type) {
        if ("USE_CASE".equals(type)) return DiagramManager.DIAGRAM_TYPE_USE_CASE_DIAGRAM;
        if ("ACTIVITY".equals(type)) return DiagramManager.DIAGRAM_TYPE_ACTIVITY_DIAGRAM;
        if ("COMPONENT".equals(type)) return DiagramManager.DIAGRAM_TYPE_COMPONENT_DIAGRAM;
        if ("PACKAGE".equals(type)) return DiagramManager.DIAGRAM_TYPE_PACKAGE_DIAGRAM;
        if ("CLASS".equals(type)) return DiagramManager.DIAGRAM_TYPE_CLASS_DIAGRAM;
        if ("COMMUNICATION".equals(type)) return DiagramManager.DIAGRAM_TYPE_COMMUNICATION_DIAGRAM;
        if ("SEQUENCE".equals(type)) return DiagramManager.DIAGRAM_TYPE_INTERACTION_DIAGRAM;
        if ("STATE".equals(type)) return DiagramManager.DIAGRAM_TYPE_STATE_DIAGRAM;
        if ("OBJECT".equals(type)) return DiagramManager.DIAGRAM_TYPE_OBJECT_DIAGRAM;
        if ("COMPOSITE".equals(type)) return DiagramManager.DIAGRAM_TYPE_COMPOSITE_STRUCTURE_DIAGRAM;
        if ("TIMING".equals(type)) return DiagramManager.DIAGRAM_TYPE_TIMING_DIAGRAM;
        if ("INTERACTION_OVERVIEW".equals(type)) return DiagramManager.DIAGRAM_TYPE_INTERACTION_OVERVIEW_DIAGRAM;
        if ("DEPLOYMENT".equals(type)) return DiagramManager.DIAGRAM_TYPE_DEPLOYMENT;
        return DiagramManager.DIAGRAM_TYPE_OVERVIEW_DIAGRAM;
    }

    private static String shapeType(String diagram, String stereotype) {
        if ("note".equals(stereotype) || "constraint".equals(stereotype)) {
            if ("USE_CASE".equals(diagram)) return IUseCaseDiagramUIModel.SHAPETYPE_NOTE;
            if ("ACTIVITY".equals(diagram)) return IActivityDiagramUIModel.SHAPETYPE_NOTE;
            if ("COMPONENT".equals(diagram)) return IComponentDiagramUIModel.SHAPETYPE_NOTE;
            if ("PACKAGE".equals(diagram)) return IPackageDiagramUIModel.SHAPETYPE_NOTE;
            if ("CLASS".equals(diagram)) return IClassDiagramUIModel.SHAPETYPE_NOTE;
            if ("COMMUNICATION".equals(diagram)) return ICommunicationDiagramUIModel.SHAPETYPE_NOTE;
            if ("STATE".equals(diagram)) return IStateDiagramUIModel.SHAPETYPE_NOTE;
            if ("COMPOSITE".equals(diagram)) return ICompositeStructureDiagramUIModel.SHAPETYPE_NOTE;
            if ("DEPLOYMENT".equals(diagram)) return IDeploymentDiagramUIModel.SHAPETYPE_NOTE;
            return IOverviewDiagramUIModel.SHAPETYPE_NOTE;
        }
        if ("USE_CASE".equals(diagram)) {
            if ("actor".equals(stereotype)) return IUseCaseDiagramUIModel.SHAPETYPE_ACTOR;
            if ("usecase".equals(stereotype)) return IUseCaseDiagramUIModel.SHAPETYPE_USE_CASE;
        }
        if ("ACTIVITY".equals(diagram)) {
            if ("decision".equals(stereotype)) return IActivityDiagramUIModel.SHAPETYPE_DECISION_NODE;
            if ("start".equals(stereotype)) return IActivityDiagramUIModel.SHAPETYPE_INITIAL_NODE;
            if ("end".equals(stereotype)) return IActivityDiagramUIModel.SHAPETYPE_ACTIVITY_FINAL_NODE;
            if ("activity".equals(stereotype) || "component".equals(stereotype)
                || "state".equals(stereotype) || "plain".equals(stereotype)) {
                return IActivityDiagramUIModel.SHAPETYPE_ACTIVITY_ACTION;
            }
        }
        if ("COMPONENT".equals(diagram) && !"note".equals(stereotype)) return IComponentDiagramUIModel.SHAPETYPE_COMPONENT;
        if ("PACKAGE".equals(diagram) && !"note".equals(stereotype)) return IPackageDiagramUIModel.SHAPETYPE_PACKAGE;
        if ("CLASS".equals(diagram) && !"note".equals(stereotype)) return IClassDiagramUIModel.SHAPETYPE_CLASS;
        if ("COMMUNICATION".equals(diagram) && "lifeline".equals(stereotype)) return ICommunicationDiagramUIModel.SHAPETYPE_COMMUNICATION_LIFE_LINE;
        if ("SEQUENCE".equals(diagram)) return IInteractionDiagramUIModel.SHAPETYPE_GENERIC_SHAPE;
        if ("STATE".equals(diagram)) {
            if ("start".equals(stereotype)) return IStateDiagramUIModel.SHAPETYPE_INITIAL_PSEUDO_STATE;
            if ("end".equals(stereotype)) return IStateDiagramUIModel.SHAPETYPE_FINAL_STATE2;
            if ("state".equals(stereotype)) return IStateDiagramUIModel.SHAPETYPE_STATE2;
        }
        if ("OBJECT".equals(diagram) && "object".equals(stereotype)) return IObjectDiagramUIModel.SHAPETYPE_INSTANCE_SPECIFICATION;
        if ("COMPOSITE".equals(diagram)) {
            return ICompositeStructureDiagramUIModel.SHAPETYPE_OCCURRENCE;
        }
        if ("INTERACTION_OVERVIEW".equals(diagram)) {
            if ("start".equals(stereotype)) return IInteractionOverviewDiagramUIModel.SHAPETYPE_INITIAL_NODE;
            if ("end".equals(stereotype)) return IInteractionOverviewDiagramUIModel.SHAPETYPE_ACTIVITY_FINAL_NODE;
            if ("decision".equals(stereotype)) return IInteractionOverviewDiagramUIModel.SHAPETYPE_DECISION_NODE;
            if ("interaction".equals(stereotype)) return IInteractionOverviewDiagramUIModel.SHAPETYPE_INTERACTION_OCCURRENCE;
        }
        if ("DEPLOYMENT".equals(diagram) && !"note".equals(stereotype)) return IDeploymentDiagramUIModel.SHAPETYPE_COMPONENT;
        return IOverviewDiagramUIModel.SHAPETYPE_GENERIC_SHAPE;
    }

    private static String connectorType(String diagram, String label, boolean dashed) {
        if ("USE_CASE".equals(diagram)) {
            if (label.contains("include")) return IUseCaseDiagramUIModel.SHAPETYPE_INCLUDE;
            if (label.contains("extend")) return IUseCaseDiagramUIModel.SHAPETYPE_EXTEND;
            return dashed ? IUseCaseDiagramUIModel.SHAPETYPE_DEPENDENCY : IUseCaseDiagramUIModel.SHAPETYPE_ASSOCIATION;
        }
        if ("ACTIVITY".equals(diagram)) return IActivityDiagramUIModel.SHAPETYPE_CONTROL_FLOW;
        if ("COMPONENT".equals(diagram)) return IComponentDiagramUIModel.SHAPETYPE_DEPENDENCY;
        if ("PACKAGE".equals(diagram)) return IPackageDiagramUIModel.SHAPETYPE_DEPENDENCY;
        if ("CLASS".equals(diagram)) return IClassDiagramUIModel.SHAPETYPE_ASSOCIATION;
        if ("SEQUENCE".equals(diagram)) return IInteractionDiagramUIModel.SHAPETYPE_GENERIC_CONNECTOR;
        if ("COMMUNICATION".equals(diagram)) return ICommunicationDiagramUIModel.SHAPETYPE_GENERIC_CONNECTOR;
        if ("STATE".equals(diagram)) return IStateDiagramUIModel.SHAPETYPE_TRANSITION2;
        if ("OBJECT".equals(diagram)) return IObjectDiagramUIModel.SHAPETYPE_ASSOCIATION;
        if ("COMPOSITE".equals(diagram)) return ICompositeStructureDiagramUIModel.SHAPETYPE_ASSOCIATION;
        if ("TIMING".equals(diagram)) return ITimingDiagramUIModel.SHAPETYPE_GENERIC_CONNECTOR;
        if ("INTERACTION_OVERVIEW".equals(diagram)) return IInteractionOverviewDiagramUIModel.SHAPETYPE_CONTROL_FLOW;
        if ("DEPLOYMENT".equals(diagram)) return IDeploymentDiagramUIModel.SHAPETYPE_DEPENDENCY;
        return IOverviewDiagramUIModel.SHAPETYPE_GENERIC_CONNECTOR;
    }

    private static void setName(IDiagramElement element, String name) {
        IModelElement model = element.getMetaModelElement();
        if (model == null) model = element.getModelElement();
        if (model != null) {
            model.setName(name);
            return;
        }
        // Some presentation-only elements do not own a caption model.
    }

    private static Point[] points(String encoded) {
        String[] values = encoded.split(";");
        Point[] result = new Point[values.length];
        for (int index = 0; index < values.length; index++) {
            String[] pair = values[index].split(",");
            result[index] = new Point(number(pair[0]), number(pair[1]));
        }
        return result;
    }

    private static int number(String value) {
        return (int) Math.round(Double.parseDouble(value) * SCALE);
    }

    private static String decode(String value) {
        return new String(Base64.getDecoder().decode(value), StandardCharsets.UTF_8);
    }

    private static Color color(String value) {
        return Color.decode(value);
    }
}

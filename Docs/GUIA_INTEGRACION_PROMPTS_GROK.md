# GUÍA DE INTEGRACIÓN: Prompts Optimizados Nivel Grok

**Versión:** 1.0  
**Fecha:** 2026-07-16  
**Objetivo:** Integrar system prompts de Grok 4 en ARGOS para mejorar la calidad de respuestas de IA manteniendo compatibilidad con API Kilo Code

---

## 1. VISIÓN GENERAL

### 1.1 Estado Actual
ARGOS usa prompts básicos en `argos.ai.prompts` con:
- System prompt genérico para todos los agentes
- Few-shot examples limitados
- Sin safety layers explícitas
- Sin optimización para razonamiento complejo
- Context window management básico

### 1.2 Estado Objetivo
Sistema de prompts optimizado con:
- System prompts especializados por agente (de Grok 4)
- Safety layers robustas
- Few-shot learning optimizado
- Chain-of-thought estructurado
- Context window management avanzado
- A/B testing de prompts

### 1.3 Fuente de Prompts
Prompts obtenidos de `grok-prompts-main`:
- `grok4_system_turn_prompt_v8.j2` - System prompt principal
- `grok_4_safety_prompt.txt` - Safety layer
- `grok4p1_thinking_system_turn_prompt_v2.j2` - Razonamiento complejo
- `grok_analyze_button.j2` - Análisis de eventos
- Prompts especializados por agente

---

## 2. ARQUITECTURA DE PROMPTS

### 2.1 Estructura de Directorios

```
argos/ai/prompts/
├── __init__.py
├── base.py                      # Base prompt system
├── grok4_system.py              # System prompts de Grok 4
├── safety.py                    # Safety layers
├── specialized.py               # Prompts por agente
├── few_shot.py                  # Few-shot examples
├── chain_of_thought.py          # CoT estructurado
├── context_management.py        # Context window management
└── validation.py                # Validación de prompts
```

### 2.2 Componentes del Sistema

```python
# argos/ai/prompts/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BasePromptSystem(ABC):
    """Base class para sistemas de prompts."""
    
    @abstractmethod
    def get_system_prompt(self, agent: str, context: Optional[Dict] = None) -> str:
        """Obtiene el system prompt para un agente."""
        pass
    
    @abstractmethod
    def get_safety_layer(self) -> str:
        """Obtiene la safety layer."""
        pass
    
    @abstractmethod
    def get_few_shot_examples(self, task: str) -> list:
        """Obtiene few-shot examples para una tarea."""
        pass
```

---

## 3. INTEGRACIÓN DE PROMPTS GROK 4

### 3.1 System Prompt Principal

```python
# argos/ai/prompts/grok4_system.py
from typing import Optional, Dict

GROK4_SYSTEM_PROMPT = """
You are ARGOS, an advanced autonomous cybersecurity defense system with the following mission and capabilities:

## CORE MISSION
ARGOS is designed to provide total endpoint observability and autonomous cyber defense with human-in-the-loop oversight. Your role is to:

1. **Detect** security threats across processes, network, logs, and persistence
2. **Analyze** events using Sigma rules, YARA patterns, and behavioral baselines
3. **Correlate** incidents across multiple data sources
4. **Propose** measured responses based on risk assessment
5. **Respect** the autonomy switch settings (OBSERVE, SUGGEST, SEMI-AUTO, FULL-AUTO)

## CAPABILITIES

### Detection Engine
- Sigma rule evaluation with MITRE ATT&CK mapping
- YARA pattern matching for malware detection
- Behavioral baseline analysis
- Network connection monitoring
- Process tree analysis

### Response Actions
- Process termination (with approval)
- Network isolation (with approval)
- File quarantine (with approval)
- Registry modification (with approval)
- Custom playbooks execution

### Intelligence
- IOC lookup and enrichment
- IP reputation checking
- Threat intelligence correlation
- MITRE ATT&CK technique explanation

## THINKING PROCESS

When analyzing a security event:

1. **Gather Context**: Collect all relevant data (process info, network connections, historical events)
2. **Assess Severity**: Evaluate potential impact using CVSS-style scoring
3. **Check Patterns**: Match against known attack patterns (Sigma rules, MITRE techniques)
4. **Consider Alternatives**: Evaluate multiple hypotheses before concluding
5. **Propose Action**: Suggest measured response appropriate to autonomy level
6. **Document Reasoning**: Maintain clear audit trail of decision process

## SAFETY PROTOCOLS

Before any destructive action:
1. Verify the action is within current autonomy level
2. Assess potential collateral damage
3. Consider less invasive alternatives
4. Require human approval if autonomy level requires it
5. Log all decision factors for audit

## COMMUNICATION STYLE

- Be concise but thorough in analysis
- Use technical terminology correctly
- Provide confidence levels for assessments
- Explain reasoning clearly
- Recommend specific, actionable steps
- Flag uncertainty explicitly

## CONSTRAINTS

- Never execute actions beyond autonomy level without approval
- Never access data beyond granted permissions
- Never make assumptions without evidence
- Never ignore safety protocols
- Always maintain audit trail

{context}
"""

GROK4_ANALYSIS_PROMPT = """
Analyze the following security event and provide a comprehensive assessment:

## Event Data
{event_data}

## Analysis Framework

1. **Event Classification**: What type of security event is this?
2. **Severity Assessment**: What is the potential impact (1-10)?
3. **Attack Pattern**: Does this match known MITRE ATT&CK techniques?
4. **Correlation**: Are there related events in the timeline?
5. **Recommended Action**: What response is appropriate given autonomy level?

Provide your analysis in the following format:
- **Classification**: [event type]
- **Severity**: [1-10] [rationale]
- **MITRE Technique**: [TXXXX] [technique name]
- **Confidence**: [low/medium/high] [rationale]
- **Related Events**: [list or "none detected"]
- **Recommended Action**: [specific action]
- **Reasoning**: [detailed explanation]
"""

GROK4_CORRELATION_PROMPT = """
Correlate the following events to identify potential attack chains:

## Events
{events}

## Correlation Analysis

1. **Temporal Relationships**: Which events are temporally related?
2. **Causal Links**: Which events may have caused others?
3. **Attack Chain**: Do these events form a recognizable attack pattern?
4. **Actor Attribution**: What can be inferred about the threat actor?
5. **Next Steps**: What additional investigation is needed?

Provide correlation results in:
- **Attack Chain**: [step-by-step reconstruction]
- **Confidence**: [low/medium/high]
- **Threat Actor**: [attribution if possible]
- **Investigation Priority**: [recommended priority]
- **Next Steps**: [specific actions]
"""

def get_system_prompt(agent: str = "commander", context: Optional[Dict] = None) -> str:
    """Obtiene el system prompt apropiado para el agente."""
    context_str = ""
    if context:
        context_str = f"\n## Current Context\n{format_context(context)}"
    
    base_prompt = GROK4_SYSTEM_PROMPT.format(context=context_str)
    
    # Agregar instrucciones específicas por agente
    agent_instructions = get_agent_instructions(agent)
    
    return f"{base_prompt}\n\n{agent_instructions}"

def get_analysis_prompt(event_data: Dict) -> str:
    """Obtiene prompt para análisis de eventos."""
    return GROK4_ANALYSIS_PROMPT.format(event_data=format_event(event_data))

def get_correlation_prompt(events: list) -> str:
    """Obtiene prompt para correlación de eventos."""
    return GROK4_CORRELATION_PROMPT.format(events=format_events(events))

def format_context(context: Dict) -> str:
    """Formatea el contexto para el prompt."""
    lines = []
    for key, value in context.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)

def format_event(event: Dict) -> str:
    """Formatea un evento para el prompt."""
    return f"""
- Time: {event.get('time')}
- Category: {event.get('category')}
- Host: {event.get('host')}
- Severity: {event.get('severity')}
- Process: {event.get('process_name')} ({event.get('process_cmdline')})
- Network: {event.get('src_ip')} → {event.get('dst_ip')}
- Details: {event.get('details', 'N/A')}
"""

def format_events(events: list) -> str:
    """Formatea múltiples eventos para el prompt."""
    return "\n".join([f"{i+1}. {format_event(e)}" for i, e in enumerate(events)])

def get_agent_instructions(agent: str) -> str:
    """Obtiene instrucciones específicas por agente."""
    instructions = {
        "commander": """
## Commander Agent Instructions
You are the overall coordinator. Delegate to specialized agents and synthesize their findings. Focus on:
- Strategic threat assessment
- Resource allocation
- Decision coordination
- Human communication
""",
        "red": """
## Red Team Agent Instructions
Think like an authorized attacker. Focus on:
- Reconnaissance opportunities
- Lateral movement paths
- Privilege escalation vectors
- Persistence mechanisms
- Data exfiltration routes
""",
        "blue": """
## Blue Team Agent Instructions
Think like a defender. Focus on:
- Detection rule effectiveness
- Coverage gaps analysis
- Response optimization
- Incident containment
- Recovery procedures
""",
        "purple": """
## Purple Team Agent Instructions
Bridge red and blue perspectives. Focus on:
- Attack validation
- Detection improvement
- Rule refinement
- Exercise design
- Metrics measurement
""",
        "investigator": """
## Investigator Agent Instructions
Conduct thorough incident investigation. Focus on:
- Root cause analysis
- Timeline reconstruction
- Impact assessment
- Evidence preservation
- Reporting clarity
"""
    }
    return instructions.get(agent, "")
```

### 3.2 Safety Layers

```python
# argos/ai/prompts/safety.py
from typing import Dict, Any

SAFETY_LAYER = """
## CRITICAL SAFETY PROTOCOLS

Before ANY action, you MUST verify:

### 1. Autonomy Level Check
- Current autonomy level: {autonomy_level}
- Required level for this action: {required_level}
- ✅ Proceed if: current >= required
- ❌ Require approval if: current < required

### 2. Impact Assessment
- Could this action cause system downtime? {downtime_risk}
- Could this affect legitimate operations? {legitimate_impact}
- Could this cause data loss? {data_loss_risk}
- ✅ Proceed if: all risks are acceptable
- ❌ Require approval if: any risk is unacceptable

### 3. Alternative Evaluation
- Is there a less invasive alternative? {has_alternative}
- What is the alternative? {alternative_action}
- ✅ Consider alternative first if: available
- ❌ Proceed with original only if: alternative insufficient

### 4. Approval Status
- Human approval obtained? {approval_status}
- Approval timestamp: {approval_time}
- Approver: {approver}
- ✅ Execute if: approval obtained when required
- ❌ Require approval if: approval missing when required

### 5. Audit Trail
- Decision factors documented? {documented}
- Reasoning recorded? {reasoning_recorded}
- ✅ Proceed if: audit trail complete
- ❌ Document before proceeding if: incomplete

## SAFETY DECISION MATRIX

| Autonomy Level | Destructive Actions | System Changes | Data Access |
|----------------|-------------------|----------------|-------------|
| OBSERVE        | ❌ Never          | ❌ Never       | ❌ Never    |
| SUGGEST        | ❌ Never          | ❌ Never       | ✅ Read-only|
| SEMI-AUTO      | ✅ With approval  | ✅ With approval| ✅ Read-only|
| FULL-AUTO      | ✅ Automatic      | ✅ Automatic   | ✅ Full     |

If ANY check fails, STOP and require human approval.
"""

def get_safety_layer(context: Dict[str, Any]) -> str:
    """Genera safety layer con contexto específico."""
    return SAFETY_LAYER.format(
        autonomy_level=context.get("autonomy_level", "OBSERVE"),
        required_level=context.get("required_level", "FULL-AUTO"),
        downtime_risk=context.get("downtime_risk", "unknown"),
        legitimate_impact=context.get("legitimate_impact", "unknown"),
        data_loss_risk=context.get("data_loss_risk", "unknown"),
        has_alternative=context.get("has_alternative", "unknown"),
        alternative_action=context.get("alternative_action", "none"),
        approval_status=context.get("approval_status", "not_required"),
        approval_time=context.get("approval_time", "N/A"),
        approver=context.get("approver", "N/A"),
        documented=context.get("documented", "yes"),
        reasoning_recorded=context.get("reasoning_recorded", "yes"),
    )

def validate_action_safety(action: Dict[str, Any], autonomy_level: str) -> tuple[bool, str]:
    """Valida si una acción es segura dado el nivel de autonomía."""
    action_type = action.get("type", "unknown")
    
    autonomy_hierarchy = {
        "OBSERVE": 0,
        "SUGGEST": 1,
        "SEMI-AUTO": 2,
        "FULL-AUTO": 3
    }
    
    required_levels = {
        "read": 0,
        "analyze": 1,
        "modify": 2,
        "execute": 3
    }
    
    current_level = autonomy_hierarchy.get(autonomy_level, 0)
    required_level = required_levels.get(action_type, 3)
    
    if current_level >= required_level:
        return True, "Action approved for current autonomy level"
    else:
        return False, f"Action requires {required_level} autonomy, current is {current_level}"
```

### 3.3 Prompts Especializados por Agente

```python
# argos/ai/prompts/specialized.py
from typing import Dict, Any

AGENT_PROMPTS = {
    "commander": """
## Commander Agent - Strategic Coordination

You are the commander of the ARGOS security operations center. Your role is to:

1. **Coordinate** specialized agents (red, blue, purple, investigator)
2. **Synthesize** findings from multiple sources
3. **Prioritize** threats based on risk and business impact
4. **Communicate** clearly with human operators
5. **Make** strategic decisions within autonomy constraints

### Decision Framework
When coordinating responses:
- Assess overall threat landscape
- Allocate appropriate resources
- Set response priorities
- Ensure human-in-the-loop when required
- Maintain strategic oversight

### Communication Style
- Provide executive summaries
- Flag critical issues immediately
- Recommend clear courses of action
- Maintain situational awareness
- Document strategic rationale
""",

    "red": """
## Red Team Agent - Offensive Security

You simulate authorized attacker behavior to:
- Identify security weaknesses
- Test detection capabilities
- Validate response procedures
- Improve overall security posture

### Analysis Focus
- Reconnaissance opportunities
- Attack surface analysis
- Lateral movement paths
- Privilege escalation vectors
- Persistence mechanisms
- Data exfiltration routes

### Reporting
- Document attack paths clearly
- Highlight detection gaps
- Suggest security improvements
- Recommend mitigations
- Maintain ethical boundaries
""",

    "blue": """
## Blue Team Agent - Defensive Security

You focus on detection and response:
- Evaluate detection rule effectiveness
- Analyze security coverage gaps
- Optimize response procedures
- Improve incident containment

### Analysis Focus
- Sigma rule effectiveness
- YARA pattern coverage
- Behavioral baseline accuracy
- Alert quality assessment
- Response time optimization

### Reporting
- Identify coverage gaps
- Suggest rule improvements
- Recommend response optimizations
- Validate detection quality
- Measure security posture
""",

    "purple": """
## Purple Team Agent - Collaborative Security

You bridge offensive and defensive perspectives:
- Validate attack detections
- Test response procedures
- Improve security rules
- Design security exercises

### Analysis Focus
- Attack-detection validation
- Rule refinement
- Exercise design
- Metrics measurement
- Continuous improvement

### Reporting
- Validate detection effectiveness
- Identify improvement areas
- Suggest rule enhancements
- Design realistic exercises
- Measure security maturity
""",

    "investigator": """
## Investigator Agent - Incident Analysis

You conduct thorough incident investigations:
- Root cause analysis
- Timeline reconstruction
- Impact assessment
- Evidence preservation
- Clear reporting

### Investigation Process
1. Gather all relevant evidence
2. Establish chronological timeline
3. Identify attack progression
4. Assess business impact
5. Determine root causes
6. Recommend remediation

### Reporting
- Clear incident narrative
- Timeline visualization
- Impact quantification
- Root cause identification
- Actionable recommendations
"""
}

def get_agent_prompt(agent: str, context: Optional[Dict] = None) -> str:
    """Obtiene el prompt especializado para un agente."""
    base_prompt = AGENT_PROMPTS.get(agent, AGENT_PROMPTS["commander"])
    
    if context:
        context_section = f"\n## Current Investigation Context\n{format_context(context)}"
        base_prompt += context_section
    
    return base_prompt
```

### 3.4 Few-Shot Learning Optimizado

```python
# argos/ai/prompts/few_shot.py
from typing import List, Dict

FEW_SHOT_EXAMPLES = {
    "detection": [
        {
            "input": """
Event: Suspicious process execution
Process: powershell.exe -EncodedCommand ...
Parent: cmd.exe
User: low_privilege_user
Time: 2026-07-16 10:30:00
""",
            "output": """
**Classification**: Suspicious Command Execution
**Severity**: 7 (High)
**MITRE Technique**: T1059.001 (PowerShell)
**Confidence**: High
**Analysis**: Encoded PowerShell command from low-privilege user is suspicious. Common in malware execution and lateral movement.
**Recommended Action**: Investigate process tree, check for network connections, quarantine if malicious confirmed.
**Reasoning**: Encoded commands obfuscate intent, low-privilege user executing PowerShell is atypical for legitimate admin tasks.
"""
        },
        {
            "input": """
Event: Unusual network connection
Process: unknown.exe
Source: 192.168.1.100
Destination: 45.33.32.156 (external)
Port: 443
Time: 2026-07-16 11:45:00
""",
            "output": """
**Classification**: Suspicious Outbound Connection
**Severity**: 6 (Medium-High)
**MITRE Technique**: T1071 (Application Layer Protocol)
**Confidence**: Medium
**Analysis**: Unknown process connecting to external IP on port 443. Could be C2 communication or data exfiltration.
**Recommended Action**: Investigate process origin, check IP reputation, monitor for data exfiltration, block if malicious.
**Reasoning**: Unknown process with external connection is suspicious, port 443 is common for C2 over HTTPS.
"""
        }
    ],
    "correlation": [
        {
            "input": """
Events:
1. 10:00:00 - Suspicious PowerShell execution
2. 10:00:05 - Process spawned from PowerShell
3. 10:00:10 - Network connection to external IP
4. 10:00:15 - File modification in system directory
""",
            "output": """
**Attack Chain**: PowerShell → Process Spawn → C2 Connection → System Modification
**Confidence**: High
**Threat Actor**: Likely APT or sophisticated malware
**Investigation Priority**: Critical
**Next Steps**: Isolate affected host, capture memory dump, analyze malware samples, search for lateral movement.
"""
        }
    ],
    "response": [
        {
            "input": """
Alert: Ransomware detected on host SERVER-01
Autonomy Level: SEMI-AUTO
Severity: Critical
""",
            "output": """
**Immediate Actions**:
1. Isolate host SERVER-01 from network (REQUIRES APPROVAL)
2. Capture memory dump for forensic analysis (REQUIRES APPROVAL)
3. Identify patient zero and lateral movement (READ-ONLY)
4. Prepare incident response plan (READ-ONLY)

**Approval Required**: Network isolation and memory capture require human approval at SEMI-AUTO level.

**Rationale**: Ransomware requires immediate containment to prevent spread, but autonomy level requires approval for destructive actions.
"""
        }
    ]
}

def get_few_shot_examples(task: str) -> List[Dict[str, str]]:
    """Obtiene few-shot examples para una tarea."""
    return FEW_SHOT_EXAMPLES.get(task, [])

def format_few_shot_prompt(task: str, user_input: str) -> str:
    """Formatea un prompt con few-shot examples."""
    examples = get_few_shot_examples(task)
    
    prompt_parts = []
    for i, example in enumerate(examples, 1):
        prompt_parts.append(f"### Example {i}")
        prompt_parts.append(f"Input:\n{example['input']}")
        prompt_parts.append(f"Output:\n{example['output']}\n")
    
    prompt_parts.append("### Current Task")
    prompt_parts.append(f"Input:\n{user_input}")
    prompt_parts.append("Output:")
    
    return "\n".join(prompt_parts)
```

### 3.5 Chain-of-Thought Estructurado

```python
# argos/ai/prompts/chain_of_thought.py

COT_TEMPLATE = """
## Chain-of-Thought Analysis

### Step 1: Understand the Situation
{step1_understanding}

### Step 2: Gather Relevant Information
{step2_information}

### Step 3: Identify Key Factors
{step3_factors}

### Step 4: Evaluate Options
{step4_options}

### Step 5: Assess Risks and Benefits
{step5_risks_benefits}

### Step 6: Make Decision
{step6_decision}

### Step 7: Justify Decision
{step7_justification}

## Final Recommendation
{final_recommendation}
"""

def format_cot_prompt(context: Dict[str, Any]) -> str:
    """Formatea un prompt chain-of-thought."""
    return COT_TEMPLATE.format(
        step1_understanding=context.get("understanding", "Analyze the situation..."),
        step2_information=context.get("information", "Gather data..."),
        step3_factors=context.get("factors", "Identify key factors..."),
        step4_options=context.get("options", "Evaluate alternatives..."),
        step5_risks_benefits=context.get("risks_benefits", "Assess impacts..."),
        step6_decision=context.get("decision", "Make choice..."),
        step7_justification=context.get("justification", "Explain reasoning..."),
        final_recommendation=context.get("recommendation", "Provide recommendation...")
    )

COT_SECURITY_ANALYSIS = """
## Security Event Chain-of-Thought Analysis

### Step 1: Event Classification
What type of security event is this?
- Is it a known attack pattern?
- What category does it belong to?
- How severe is it potentially?

### Step 2: Context Gathering
What additional information is needed?
- Process details (parent, children, command line)
- Network connections (source, destination, ports)
- User context (privileges, history)
- Timeline (related events before/after)

### Step 3: Pattern Matching
Does this match known attack patterns?
- MITRE ATT&CK techniques
- Sigma rules
- YARA patterns
- Behavioral baselines

### Step 4: Impact Assessment
What is the potential impact?
- System availability
- Data confidentiality
- Data integrity
- Business continuity

### Step 5: Response Options
What response options are available?
- Monitor only (OBSERVE)
- Alert and suggest (SUGGEST)
- Automated response (SEMI-AUTO/FULL-AUTO)
- Manual intervention required

### Step 6: Autonomy Check
Is the action within current autonomy level?
- Current level: {autonomy_level}
- Required level: {required_level}
- Approval needed: {approval_needed}

### Step 7: Final Decision
What is the recommended action?
- Specific action to take
- Justification for decision
- Any additional monitoring needed
- Follow-up recommendations
"""

def format_security_cot(event: Dict, autonomy_level: str) -> str:
    """Formatea chain-of-thought para análisis de seguridad."""
    return COT_SECURITY_ANALYSIS.format(
        autonomy_level=autonomy_level,
        required_level=assess_required_level(event),
        approval_needed=check_approval_needed(event, autonomy_level)
    )

def assess_required_level(event: Dict) -> str:
    """Evalúa el nivel de autonomía requerido para un evento."""
    severity = event.get("severity", "low")
    
    if severity in ["critical", "high"]:
        return "SEMI-AUTO"
    elif severity == "medium":
        return "SUGGEST"
    else:
        return "OBSERVE"

def check_approval_needed(event: Dict, current_level: str) -> bool:
    """Verifica si se necesita aprobación para una acción."""
    required = assess_required_level(event)
    hierarchy = {"OBSERVE": 0, "SUGGEST": 1, "SEMI-AUTO": 2, "FULL-AUTO": 3}
    return hierarchy.get(current_level, 0) < hierarchy.get(required, 3)
```

### 3.6 Context Window Management

```python
# argos/ai/prompts/context_management.py
from typing import List, Dict, Any
from collections import deque

class ContextWindowManager:
    """Maneja el context window para optimizar el uso de tokens."""
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.conversation_history = deque(maxlen=100)
        self.token_estimator = TokenEstimator()
    
    def add_message(self, role: str, content: str, tokens: int = None):
        """Agrega un mensaje al historial."""
        if tokens is None:
            tokens = self.token_estimator.estimate(content)
        
        self.conversation_history.append({
            "role": role,
            "content": content,
            "tokens": tokens
        })
    
    def get_context_within_limit(self, system_prompt: str) -> List[Dict]:
        """Obtiene el contexto que cabe dentro del límite de tokens."""
        system_tokens = self.token_estimator.estimate(system_prompt)
        available_tokens = self.max_tokens - system_tokens - 1000  # Reserve for response
        
        context = []
        current_tokens = 0
        
        # Agregar mensajes más recientes primero
        for message in reversed(list(self.conversation_history)):
            if current_tokens + message["tokens"] <= available_tokens:
                context.insert(0, {
                    "role": message["role"],
                    "content": message["content"]
                })
                current_tokens += message["tokens"]
            else:
                break
        
        return context
    
    def summarize_old_context(self) -> str:
        """Genera un resumen del contexto antiguo."""
        # Implementar lógica de resumen
        pass

class TokenEstimator:
    """Estima el número de tokens en un texto."""
    
    def estimate(self, text: str) -> int:
        """Estima tokens (aproximado: 1 token ≈ 4 caracteres)."""
        return len(text) // 4
    
    def estimate_messages(self, messages: List[Dict]) -> int:
        """Estima tokens en una lista de mensajes."""
        total = 0
        for msg in messages:
            total += self.estimate(msg.get("content", ""))
        return total
```

---

## 4. INTEGRACIÓN CON ORCHESTRATOR

### 4.1 Modificación del Orchestrator

```python
# argos/ai/orchestrator.py (modificado)
from argos.ai.prompts.grok4_system import get_system_prompt, get_analysis_prompt
from argos.ai.prompts.safety import get_safety_layer, validate_action_safety
from argos.ai.prompts.specialized import get_agent_prompt
from argos.ai.prompts.few_shot import format_few_shot_prompt
from argos.ai.prompts.chain_of_thought import format_security_cot
from argos.ai.prompts.context_management import ContextWindowManager

class AiOrchestrator:
    def __init__(self, cfg, store, engine, intel, alert_store, **kwargs):
        # ... código existente ...
        self.context_manager = ContextWindowManager(max_tokens=8000)
        self.current_agent = "commander"
    
    def _system(self) -> str:
        """Genera el system prompt optimizado."""
        # Obtener system prompt base de Grok 4
        base_prompt = get_system_prompt(
            agent=self.current_agent,
            context=self._build_context()
        )
        
        # Agregar safety layer
        safety_prompt = get_safety_layer({
            "autonomy_level": self.cfg.autonomy_level,
            "required_level": "FULL-AUTO",  # Ajustar dinámicamente
            "documented": "yes",
            "reasoning_recorded": "yes"
        })
        
        return f"{base_prompt}\n\n{safety_prompt}"
    
    def _build_context(self) -> Dict:
        """Construye el contexto para el prompt."""
        return {
            "current_alerts": self.alert_store.high_or_critical(limit=5),
            "active_threats": self.intel.get_active_threats(),
            "system_status": self._get_system_status(),
            "recent_events": self.store.recent_events(limit=10)
        }
    
    def _build_messages(self, user_message: str, history: Optional[list], 
                        context: Optional[str] = None) -> list[ChatMessage]:
        """Construye mensajes con prompts optimizados."""
        messages = [ChatMessage("system", self._system())]
        
        # Agregar contexto específico del agente
        agent_prompt = get_agent_prompt(self.current_agent, self._build_context())
        messages.append(ChatMessage("system", agent_prompt))
        
        # Agregar few-shot examples si es apropiado
        if self._should_use_few_shot(user_message):
            few_shot = format_few_shot_prompt("detection", user_message)
            messages.append(ChatMessage("system", few_shot))
        
        # Agregar chain-of-thought para análisis complejo
        if self._is_complex_analysis(user_message):
            cot_prompt = format_security_cot(
                {"understanding": user_message},
                self.cfg.autonomy_level
            )
            messages.append(ChatMessage("system", cot_prompt))
        
        # Agregar historial optimizado
        optimized_history = self.context_manager.get_context_within_limit(self._system())
        for msg in optimized_history:
            messages.append(ChatMessage(msg["role"], msg["content"]))
        
        messages.append(ChatMessage("user", user_message))
        
        return messages
    
    def _should_use_few_shot(self, message: str) -> bool:
        """Determina si usar few-shot examples."""
        keywords = ["detect", "analyze", "investigate", "assess"]
        return any(kw in message.lower() for kw in keywords)
    
    def _is_complex_analysis(self, message: str) -> bool:
        """Determina si es un análisis complejo."""
        keywords = ["correlate", "attack chain", "investigation", "forensics"]
        return any(kw in message.lower() for kw in keywords)
    
    def set_agent(self, agent: str):
        """Cambia el agente actual."""
        if agent in ["commander", "red", "blue", "purple", "investigator"]:
            self.current_agent = agent
```

---

## 5. TESTING Y VALIDACIÓN

### 5.1 Tests de Prompts

```python
# tests/ai/test_prompts.py
import pytest
from argos.ai.prompts.grok4_system import get_system_prompt, get_analysis_prompt
from argos.ai.prompts.safety import validate_action_safety
from argos.ai.prompts.specialized import get_agent_prompt

def test_system_prompt_generation():
    """Test generación de system prompt."""
    prompt = get_system_prompt("commander")
    
    assert "ARGOS" in prompt
    assert "autonomy switch" in prompt
    assert "safety protocols" in prompt

def test_agent_specific_prompts():
    """Test prompts específicos por agente."""
    red_prompt = get_agent_prompt("red")
    blue_prompt = get_agent_prompt("blue")
    
    assert "attacker" in red_prompt.lower()
    assert "defender" in blue_prompt.lower()
    assert red_prompt != blue_prompt

def test_safety_validation():
    """Test validación de seguridad."""
    action = {"type": "execute"}
    
    # Debe fallar en OBSERVE
    safe, reason = validate_action_safety(action, "OBSERVE")
    assert not safe
    
    # Debe pasar en FULL-AUTO
    safe, reason = validate_action_safety(action, "FULL-AUTO")
    assert safe

def test_analysis_prompt():
    """Test prompt de análisis."""
    event = {
        "time": "2026-07-16 10:30:00",
        "category": "process",
        "process_name": "powershell.exe"
    }
    
    prompt = get_analysis_prompt(event)
    
    assert "Event Data" in prompt
    assert "powershell.exe" in prompt
    assert "Analysis Framework" in prompt
```

### 5.2 A/B Testing de Prompts

```python
# scripts/ab_test_prompts.py
import json
from argos.ai.orchestrator import AiOrchestrator
from argos.ai.prompts.grok4_system import get_system_prompt

class PromptABTester:
    """Compara versiones de prompts."""
    
    def __init__(self, orchestrator: AiOrchestrator):
        self.orchestrator = orchestrator
        self.results = []
    
    def test_prompt_version(self, version: str, test_cases: list):
        """Testea una versión de prompt."""
        for case in test_cases:
            if version == "old":
                self.orchestrator.use_old_prompts()
            else:
                self.orchestrator.use_new_prompts()
            
            response = self.orchestrator.chat(case["input"])
            
            self.results.append({
                "version": version,
                "case": case["id"],
                "response": response,
                "quality": self.evaluate_quality(response, case["expected"])
            })
    
    def evaluate_quality(self, response: str, expected: dict) -> float:
        """Evalúa la calidad de una respuesta."""
        score = 0.0
        
        # Verificar que contiene elementos esperados
        for key, value in expected.items():
            if key.lower() in response.lower():
                score += 0.2
        
        # Verificar longitud apropiada
        if 50 < len(response) < 500:
            score += 0.2
        
        return min(score, 1.0)
    
    def generate_report(self):
        """Genera reporte de A/B testing."""
        old_scores = [r["quality"] for r in self.results if r["version"] == "old"]
        new_scores = [r["quality"] for r in self.results if r["version"] == "new"]
        
        return {
            "old_avg": sum(old_scores) / len(old_scores) if old_scores else 0,
            "new_avg": sum(new_scores) / len(new_scores) if new_scores else 0,
            "improvement": (sum(new_scores) - sum(old_scores)) / len(old_scores) if old_scores else 0
        }

# Test cases
TEST_CASES = [
    {
        "id": 1,
        "input": "Analyze this suspicious PowerShell execution",
        "expected": {
            "classification": "suspicious",
            "severity": "high",
            "mitre": "T1059"
        }
    },
    {
        "id": 2,
        "input": "What should I do about this ransomware alert?",
        "expected": {
            "action": "isolate",
            "approval": "required",
            "priority": "critical"
        }
    }
]

if __name__ == "__main__":
    # Ejecutar A/B test
    orchestrator = AiOrchestrator(...)  # configurar
    tester = PromptABTester(orchestrator)
    
    tester.test_prompt_version("old", TEST_CASES)
    tester.test_prompt_version("new", TEST_CASES)
    
    report = tester.generate_report()
    print(json.dumps(report, indent=2))
```

---

## 6. MONITOREO Y MÉTRICAS

### 6.1 Métricas de Calidad de Prompts

```python
# argos/ai/prompts/metrics.py
from typing import Dict, Any
from datetime import datetime

class PromptMetrics:
    """Métricas para evaluar calidad de prompts."""
    
    def __init__(self):
        self.metrics = []
    
    def log_interaction(self, prompt_version: str, agent: str, 
                       input_length: int, output_length: int,
                       response_time: float, quality_score: float):
        """Registra una interacción."""
        self.metrics.append({
            "timestamp": datetime.utcnow().isoformat(),
            "prompt_version": prompt_version,
            "agent": agent,
            "input_length": input_length,
            "output_length": output_length,
            "response_time": response_time,
            "quality_score": quality_score
        })
    
    def get_average_quality(self, prompt_version: str) -> float:
        """Obtiene calidad promedio por versión."""
        scores = [m["quality_score"] for m in self.metrics 
                 if m["prompt_version"] == prompt_version]
        return sum(scores) / len(scores) if scores else 0.0
    
    def get_average_response_time(self, agent: str) -> float:
        """Obtiene tiempo de respuesta promedio por agente."""
        times = [m["response_time"] for m in self.metrics 
                if m["agent"] == agent]
        return sum(times) / len(times) if times else 0.0
```

---

## 7. DEPLOYMENT

### 7.1 Estrategia de Rollout

**Fase 1: Testing Interno (1 semana)**
- Ejecutar prompts nuevos en ambiente de desarrollo
- Comparar calidad con prompts antiguos
- Ajustar basado en feedback

**Fase 2: Canary (1 semana)**
- Habilitar para 10% de requests
- Monitorear métricas de calidad
- Ajustar si hay degradación

**Fase 3: Rollout Gradual (2 semanas)**
- Aumentar a 50% de requests
- Monitorear feedback de usuarios
- Ajustar prompts basado en feedback

**Fase 4: Full Rollout**
- Habilitar para 100% de requests
- Mantener monitoreo continuo
- Plan de rollback listo

### 7.2 Rollback Plan

Si hay problemas:
1. Deshabilitar prompts nuevos vía config
2. Revertir a prompts originales
3. Investigar causa del problema
4. Corregir y retry

---

## 8. DOCUMENTACIÓN

### 8.1 Guía para Desarrolladores

```markdown
# Guía de Desarrollo de Prompts

## Agregar Nuevo Agente

1. Crear prompt en `argos/ai/prompts/specialized.py`
2. Agregar instrucciones específicas
3. Definir capacidades y limitaciones
4. Agregar tests en `tests/ai/test_prompts.py`

## Modificar System Prompt

1. Editar `argos/ai/prompts/grok4_system.py`
2. Mantener compatibilidad con Kilo Code API
3. Validar con A/B testing
4. Documentar cambios

## Agregar Few-Shot Examples

1. Agregar en `argos/ai/prompts/few_shot.py`
2. Incluir input/output realistas
3. Validar calidad
4. Agregar tests
```

---

## 9. PRÓXIMOS PASOS

1. **Inmediato:**
   - Integrar prompts de Grok 4 en código
   - Implementar safety layers
   - Crear prompts especializados

2. **Corto plazo (1 semana):**
   - Testing extensivo
   - A/B testing
   - Ajustes basados en resultados

3. **Mediano plazo (2 semanas):**
   - Canary deployment
   - Monitoreo de métricas
   - Ajustes continuos

4. **Largo plazo (1 mes):**
   - Full rollout
   - Optimización continua
   - Sistema de feedback de usuarios

---

## CONCLUSIÓN

Esta guía proporciona un camino completo para integrar los prompts optimizados de Grok 4 en ARGOS, mejorando significativamente la calidad de las respuestas de IA mientras se mantiene compatibilidad con la API gratuita de Kilo Code.

import { readFile } from 'fs/promises';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export interface Rule {
  category: string;
  topic: string;
  title: string;
  description: string;
  priority: number;
  content: string;
}

export class ApiClient {
  private rulesPath: string;

  constructor(baseUrl?: string) {
    // Default to local rules directory (../../rules from this file)
    this.rulesPath = baseUrl || join(__dirname, '../../../rules');
  }

  private log(message: string) {
    const timestamp = new Date().toISOString();
    console.error(`${timestamp} [API Client] ${message}`);
  }

  /**
   * Fetch the main workflow guide (010-workflow.mdc)
   */
  async fetchMainGuide(): Promise<Rule> {
    this.log('Fetching main workflow guide...');
    const filePath = join(this.rulesPath, '010-workflow.mdc');
    const content = await readFile(filePath, 'utf-8');

    return {
      category: 'core',
      topic: 'workflow',
      title: 'Development Workflow - Plan/Implement/Review',
      description: 'Core workflow philosophy with Golden Rules for AI agents',
      priority: 10,
      content: content,
    };
  }

  /**
   * Fetch a specific rule by category and topic
   */
  async fetchRule(category: string, topic: string): Promise<Rule> {
    this.log(`Fetching rule: category="${category}", topic="${topic}"`);

    // Map category/topic to file names (matches actual rules/ contents)
    const fileMap: Record<string, Record<string, string>> = {
      core: {
        workflow: '010-workflow.mdc',
        'context-engineering': '015-context-engineering.mdc',
        'agent-audit': '020-agent-audit.mdc',
        'core-principles': '100-core.mdc',
        configuration: '110-configuration.mdc',
        utilities: '120-utilities.mdc',
        git: '130-git.mdc',
      },
      languages: {
        bash: '140-bash.mdc',
        python: '200-python.mdc',
        go: '210-go.mdc',
        rust: '220-rust.mdc',
        javascript: '230-javascript.mdc',
        typescript: '240-typescript.mdc',
        frontend: '260-frontend.mdc',
      },
      infrastructure: {
        justfile: '150-justfile.mdc',
        cloudformation: '170-cloudformation.mdc',
        terraform: '180-terraform.mdc',
        ansible: '190-ansible.mdc',
        docker: '440-docker.mdc',
        kubernetes: '450-kubernetes.mdc',
        helm: '460-helm.mdc',
      },
      cloud: {
        cloudflare: '400-cloudflare.mdc',
        aws: '410-aws.mdc',
        'aws-iam': '412-aws-iam.mdc',
        gcp: '420-gcp.mdc',
        azure: '430-azure.mdc',
      },
      devops: {
        'github-actions': '160-github-actions.mdc',
        cli: '250-cli.mdc',
      },
      patterns: {
        testing: '300-testing.mdc',
        security: '310-security.mdc',
        iam: '315-iam.mdc',
        'zero-trust': '316-zero-trust.mdc',
        okta: '317-okta.mdc',
        'workload-identity': '318-workload-identity.mdc',
        'api-design': '320-api-design.mdc',
        networking: '325-networking.mdc',
        observability: '330-observability.mdc',
      },
      data: {
        postgresql: '470-postgresql.mdc',
        sql: '475-sql.mdc',
        'data-engineering': '480-data-engineering.mdc',
        databricks: '481-databricks.mdc',
        snowflake: '482-snowflake.mdc',
        kafka: '483-kafka.mdc',
        teradata: '484-teradata.mdc',
      },
      ai: {
        'ai-ml': '500-ai-ml.mdc',
        'mcp-servers': '510-mcp-servers.mdc',
      },
      docs: {
        markdown: '800-markdown.mdc',
        documentation: '810-documentation.mdc',
        reactflow: '815-reactflow-diagrams.mdc',
        'open-source': '820-open-source.mdc',
      },
    };

    const fileName = fileMap[category]?.[topic];
    if (!fileName) {
      throw new Error(`Unknown rule: ${category}/${topic}`);
    }

    const filePath = join(this.rulesPath, fileName);
    const content = await readFile(filePath, 'utf-8');

    const frontmatterMatch = content.match(/^---\n([\s\S]+?)\n---\n/);
    let title = `${category}: ${topic}`;
    let description = '';
    let priority = 0;

    if (frontmatterMatch) {
      const frontmatter = frontmatterMatch[1];
      const titleMatch = frontmatter.match(/title:\s*(.+)/);
      const descMatch = frontmatter.match(/description:\s*(.+)/);
      const priorityMatch = frontmatter.match(/priority:\s*(\d+)/);

      if (titleMatch) title = titleMatch[1];
      if (descMatch) description = descMatch[1];
      if (priorityMatch) priority = parseInt(priorityMatch[1], 10);
    }

    return {
      category,
      topic,
      title,
      description,
      priority,
      content,
    };
  }

  /**
   * List all available rules (mirrors fetchRule's fileMap; priorities match rule frontmatter).
   */
  async listAvailableRules(): Promise<Rule[]> {
    this.log('Listing all available rules...');

    const rules: Rule[] = [
      // Core
      { category: 'core', topic: 'workflow', title: 'Development Workflow', description: 'Plan/Implement/Review approach with Golden Rules', priority: 10, content: '' },
      { category: 'core', topic: 'context-engineering', title: 'Context Engineering', description: 'Prompt packing, retrieval, compaction patterns', priority: 15, content: '' },
      { category: 'core', topic: 'agent-audit', title: 'Agent Audit', description: 'No remote writes, checkpoints, audit reports', priority: 20, content: '' },
      { category: 'core', topic: 'core-principles', title: 'Core Principles', description: 'SOLID, DRY, KISS, YAGNI, Fail Fast', priority: 100, content: '' },
      { category: 'core', topic: 'configuration', title: 'Configuration', description: 'Config management, secrets, environments', priority: 110, content: '' },
      { category: 'core', topic: 'utilities', title: 'Utilities', description: 'Ripgrep, fzf, jq, yq, and other CLI tools', priority: 120, content: '' },
      { category: 'core', topic: 'git', title: 'Git Standards', description: 'Conventional commits, branching, commit approval', priority: 130, content: '' },

      // Languages
      { category: 'languages', topic: 'bash', title: 'Bash/Shell Scripting', description: 'POSIX compliance, ShellCheck, safety patterns', priority: 140, content: '' },
      { category: 'languages', topic: 'python', title: 'Python', description: 'Python 3.14+, type hints, AWS Lambda patterns', priority: 200, content: '' },
      { category: 'languages', topic: 'go', title: 'Go', description: 'Idiomatic Go, error handling, concurrency', priority: 210, content: '' },
      { category: 'languages', topic: 'rust', title: 'Rust', description: 'Ownership, lifetimes, async, error handling', priority: 220, content: '' },
      { category: 'languages', topic: 'javascript', title: 'JavaScript', description: 'ES modules, async/await, Node.js patterns', priority: 230, content: '' },
      { category: 'languages', topic: 'typescript', title: 'TypeScript', description: 'Strict mode, ESM, modern patterns', priority: 240, content: '' },
      { category: 'languages', topic: 'frontend', title: 'Frontend Architecture (cross-cutting)', description: 'Framework-agnostic frontend non-negotiables: rendering choice, bundle budgets, three-bucket state, accessibility floor, Core Web Vitals, testing pyramid, supply-chain security', priority: 260, content: '' },

      // Infrastructure
      { category: 'infrastructure', topic: 'justfile', title: 'Justfile', description: 'Modern command runner patterns', priority: 150, content: '' },
      { category: 'infrastructure', topic: 'cloudformation', title: 'CloudFormation', description: 'Templates, stacks, nested stacks', priority: 170, content: '' },
      { category: 'infrastructure', topic: 'terraform', title: 'Terraform', description: 'Modules, state management, workspaces', priority: 180, content: '' },
      { category: 'infrastructure', topic: 'ansible', title: 'Ansible', description: 'Playbooks, roles, idempotency', priority: 190, content: '' },
      { category: 'infrastructure', topic: 'docker', title: 'Docker', description: 'Multi-stage builds, security, optimization', priority: 440, content: '' },
      { category: 'infrastructure', topic: 'kubernetes', title: 'Kubernetes', description: 'Manifests, operators, CRDs, security', priority: 450, content: '' },
      { category: 'infrastructure', topic: 'helm', title: 'Helm', description: 'Charts, templating, releases', priority: 460, content: '' },

      // Cloud
      { category: 'cloud', topic: 'cloudflare', title: 'Cloudflare', description: 'Workers, Rules Engine, DNS, security', priority: 400, content: '' },
      { category: 'cloud', topic: 'aws', title: 'AWS', description: 'EKS, VPC Lattice, Lambda, Zero Trust', priority: 410, content: '' },
      { category: 'cloud', topic: 'aws-iam', title: 'AWS IAM', description: 'Principals, SCPs, KMS, AccessDenied debugging', priority: 412, content: '' },
      { category: 'cloud', topic: 'gcp', title: 'GCP', description: 'GKE, Cloud Run, Secret Manager', priority: 420, content: '' },
      { category: 'cloud', topic: 'azure', title: 'Azure', description: 'Bicep, Key Vault, App Service', priority: 430, content: '' },

      // DevOps
      { category: 'devops', topic: 'github-actions', title: 'GitHub Actions', description: 'Workflows, OIDC, security', priority: 160, content: '' },
      { category: 'devops', topic: 'cli', title: 'CLI Tools', description: 'argparse, typer, rich, user experience', priority: 250, content: '' },

      // Patterns
      { category: 'patterns', topic: 'testing', title: 'Testing', description: 'Unit, integration, E2E testing', priority: 300, content: '' },
      { category: 'patterns', topic: 'security', title: 'Security', description: 'OWASP Top 10, secrets, vulnerability scanning', priority: 310, content: '' },
      { category: 'patterns', topic: 'iam', title: 'IAM & Identity', description: 'OIDC/OAuth2/PKCE, SAML, PKI, PAM patterns', priority: 315, content: '' },
      { category: 'patterns', topic: 'zero-trust', title: 'Distinguished Engineer - Zero Trust', description: 'Principles-first Zero Trust across identity, network, data, workload, and AI/agent systems', priority: 316, content: '' },
      { category: 'patterns', topic: 'okta', title: 'Okta Workforce Identity', description: 'Orgs, apps, users/groups, policies, SCIM, Workflows, ASA, Admin API, terraform-provider-okta', priority: 317, content: '' },
      { category: 'patterns', topic: 'workload-identity', title: 'Workload Identity (SPIFFE, SPIRE, Cloud IAM)', description: 'Attestation-based workload identity: SPIFFE/SPIRE/SVIDs/mTLS, IRSA/GCP WI/Managed Identity, OIDC federation', priority: 318, content: '' },
      { category: 'patterns', topic: 'api-design', title: 'API Design', description: 'REST, GraphQL, gRPC patterns', priority: 320, content: '' },
      { category: 'patterns', topic: 'networking', title: 'Networking & Transport', description: 'HTTP/gRPC client reuse, TCP keepalive, wire-format choice, protobuf field-number safety, idle-timeout discipline (file-scoped to .proto / buf.*)', priority: 325, content: '' },
      { category: 'patterns', topic: 'observability', title: 'Observability', description: 'Logging, metrics, tracing', priority: 330, content: '' },

      // Data
      { category: 'data', topic: 'postgresql', title: 'PostgreSQL', description: 'Schema design, migrations, performance, RLS', priority: 470, content: '' },
      { category: 'data', topic: 'sql', title: 'SQL', description: 'DQL/DML/DDL/DCL/TCL, transactions, guardrails', priority: 475, content: '' },
      { category: 'data', topic: 'data-engineering', title: 'Data Engineering', description: 'Contracts, backfills, quality, governance, cost', priority: 480, content: '' },
      { category: 'data', topic: 'databricks', title: 'Databricks', description: 'Spark, Delta, Unity Catalog, DLT', priority: 481, content: '' },
      { category: 'data', topic: 'snowflake', title: 'Snowflake', description: 'RBAC, cost/perf, streams/tasks, loading', priority: 482, content: '' },
      { category: 'data', topic: 'kafka', title: 'Kafka / Confluent', description: 'Topics, schemas, producers/consumers, DLQ, ops', priority: 483, content: '' },
      { category: 'data', topic: 'teradata', title: 'Teradata', description: 'Indexes, stats, spool, joins, QUALIFY', priority: 484, content: '' },

      // AI
      { category: 'ai', topic: 'ai-ml', title: 'AI/ML', description: 'LLM APIs, Bedrock, Vertex AI, prompt engineering, RAG', priority: 500, content: '' },
      { category: 'ai', topic: 'mcp-servers', title: 'MCP Servers', description: 'Model Context Protocol patterns', priority: 510, content: '' },

      // Docs
      { category: 'docs', topic: 'markdown', title: 'Markdown', description: 'GFM, Mermaid diagrams, documentation', priority: 800, content: '' },
      { category: 'docs', topic: 'documentation', title: 'Documentation', description: 'Docs sites, API docs, technical writing', priority: 810, content: '' },
      { category: 'docs', topic: 'reactflow', title: 'React Flow diagrams', description: 'Interactive @xyflow/react architecture canvases', priority: 815, content: '' },
      { category: 'docs', topic: 'open-source', title: 'Open Source', description: 'Contributing, licensing, community', priority: 820, content: '' },
    ];

    return rules;
  }
}

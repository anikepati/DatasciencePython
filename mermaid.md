Prompt chain
graph LR
    User --> Prompt1[Prompt 1]
    User --> PromptDots[...]
    User --> PromptN[Prompt n]

    Prompt1 --> Agent1[Agent 1]
    PromptDots --> AgentDots[...]
    PromptN --> AgentN[Agent n]

    Agent1 --> AgentDots
    AgentDots --> AgentN
    
    AgentN --> Output
    Output --> User


Context
graph TD
    subgraph Context Engineering
        PE("fa:fa-terminal Prompt Engineering")
        SO("fa:fa-right-from-bracket Structured Outputs")
        RAG("fa:fa-database RAG")
        SH("fa:fa-clipboard-list State/History")
        M("fa:fa-sd-card Memory")
    end

    %% Define the overlaps/intersections
    PE <--> SO
    PE <--> RAG
    PE <--> SH
    SO <--> M
    RAG <--> SH
    SH <--> M

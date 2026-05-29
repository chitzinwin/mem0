import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight, User, Building, Hash, Tag } from "lucide-react";
import { cn } from "@/lib/utils";
import { Memory, Entity } from "@/components/types";

interface EntityGroupedMemoriesProps {
  memories: Memory[];
  onMemoryClick: (memoryId: string) => void;
  className?: string;
}

const entityTypeConfig = {
  PERSON: { icon: User, color: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  ORG: { icon: Building, color: "bg-green-500/20 text-green-300 border-green-500/30" },
  PROPER: { icon: Hash, color: "bg-purple-500/20 text-purple-300 border-purple-500/30" },
  COMPOUND: { icon: Tag, color: "bg-orange-500/20 text-orange-300 border-orange-500/30" },
};

export function EntityGroupedMemories({ 
  memories, 
  onMemoryClick, 
  className 
}: EntityGroupedMemoriesProps) {
  const [expandedEntities, setExpandedEntities] = useState<Set<string>>(new Set());

  // Group memories by entities
  const entityGroups = memories.reduce((acc, memory) => {
    if (!memory.entities || memory.entities.length === 0) {
      // Memories without entities go to "Other" group
      if (!acc["Other"]) {
        acc["Other"] = { memories: [], entityType: "COMPOUND" as const };
      }
      acc["Other"].memories.push(memory);
    } else {
      // Group by each entity
      memory.entities.forEach(entity => {
        if (!acc[entity.text]) {
          acc[entity.text] = { memories: [], entityType: entity.type };
        }
        acc[entity.text].memories.push(memory);
      });
    }
    return acc;
  }, {} as Record<string, { memories: Memory[], entityType: Entity["type"] }>);

  const toggleEntity = (entityName: string) => {
    const newExpanded = new Set(expandedEntities);
    if (newExpanded.has(entityName)) {
      newExpanded.delete(entityName);
    } else {
      newExpanded.add(entityName);
    }
    setExpandedEntities(newExpanded);
  };

  if (Object.keys(entityGroups).length === 0) {
    return (
      <div className={cn("text-center text-zinc-500 py-8", className)}>
        <Tag className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No memories to group by entities</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {Object.entries(entityGroups)
        .sort(([, a], [, b]) => b.memories.length - a.memories.length) // Sort by memory count
        .map(([entityName, { memories: entityMemories, entityType }]) => {
          const config = entityTypeConfig[entityType];
          const Icon = config.icon;
          const isExpanded = expandedEntities.has(entityName);

          return (
            <Card key={entityName} className="bg-zinc-900 border-zinc-800">
              <Collapsible
                open={isExpanded}
                onOpenChange={() => toggleEntity(entityName)}
              >
                <CollapsibleTrigger asChild>
                  <CardHeader className="pb-3 cursor-pointer hover:bg-zinc-800/50 transition-colors">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg font-medium text-white flex items-center gap-3">
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4 text-zinc-400" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-zinc-400" />
                        )}
                        <Badge
                          variant="secondary"
                          className={cn("text-sm", config.color)}
                        >
                          <Icon className="w-4 h-4 mr-2" />
                          {entityName}
                        </Badge>
                      </CardTitle>
                      <span className="text-sm text-zinc-400">
                        {entityMemories.length} {entityMemories.length === 1 ? 'memory' : 'memories'}
                      </span>
                    </div>
                  </CardHeader>
                </CollapsibleTrigger>
                
                <CollapsibleContent>
                  <CardContent className="pt-0">
                    <div className="space-y-2">
                      {entityMemories.map((memory) => (
                        <Button
                          key={memory.id}
                          variant="ghost"
                          className="w-full h-auto p-3 text-left justify-start hover:bg-zinc-800"
                          onClick={() => onMemoryClick(memory.id)}
                        >
                          <div className="flex-1">
                            <p className="text-white text-sm font-medium line-clamp-2">
                              {memory.memory}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-zinc-500">
                                {new Date(memory.created_at * 1000).toLocaleDateString()}
                              </span>
                              {memory.app_name && (
                                <Badge variant="outline" className="text-xs">
                                  {memory.app_name}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                </CollapsibleContent>
              </Collapsible>
            </Card>
          );
        })}
    </div>
  );
}
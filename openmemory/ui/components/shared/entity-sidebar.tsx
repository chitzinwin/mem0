import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Search, User, Building, Hash, Tag, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Entity } from "@/components/types";

interface EntitySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onEntitySelect: (entityName: string) => void;
  selectedEntity?: string;
  className?: string;
}

const entityTypeConfig = {
  PERSON: { icon: User, color: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  ORG: { icon: Building, color: "bg-green-500/20 text-green-300 border-green-500/30" },
  PROPER: { icon: Hash, color: "bg-purple-500/20 text-purple-300 border-purple-500/30" },
  COMPOUND: { icon: Tag, color: "bg-orange-500/20 text-orange-300 border-orange-500/30" },
};

export function EntitySidebar({ 
  isOpen, 
  onClose, 
  onEntitySelect, 
  selectedEntity,
  className 
}: EntitySidebarProps) {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [filteredEntities, setFilteredEntities] = useState<Entity[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);

  // Fetch real entities from API
  useEffect(() => {
    const fetchEntities = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/v1/entities/?user_id=winc`);
        if (response.ok) {
          const data = await response.json();
          // Transform API response to Entity format
          const apiEntities: Entity[] = data.map((entity: any) => ({
            text: entity.id || "Unknown",
            type: entity.type?.toUpperCase() || "COMPOUND",
            linked_memories: [] // TODO: Get memory count from API
          }));
          setEntities(apiEntities);
          setFilteredEntities(apiEntities);
        } else {
          console.error("Failed to fetch entities:", response.statusText);
          // Fallback to mock data if API fails
          const mockEntities: Entity[] = [
            { text: "Emma Watson", type: "PERSON", linked_memories: ["1", "2"] },
            { text: "Netflix", type: "ORG", linked_memories: ["1", "3", "4"] },
            { text: "David Kim", type: "PERSON", linked_memories: ["2"] },
            { text: "Microsoft", type: "ORG", linked_memories: ["3"] },
            { text: "React", type: "PROPER", linked_memories: ["4", "5"] },
            { text: "Software Architecture", type: "COMPOUND", linked_memories: ["1", "5"] },
          ];
          setEntities(mockEntities);
          setFilteredEntities(mockEntities);
        }
      } catch (error) {
        console.error("Error fetching entities:", error);
        // Fallback to mock data on error
        const mockEntities: Entity[] = [
          { text: "Emma Watson", type: "PERSON", linked_memories: ["1", "2"] },
          { text: "Netflix", type: "ORG", linked_memories: ["1", "3", "4"] },
        ];
        setEntities(mockEntities);
        setFilteredEntities(mockEntities);
      } finally {
        setLoading(false);
      }
    };

    if (isOpen) {
      fetchEntities();
    }
  }, [isOpen]);

  useEffect(() => {
    if (searchQuery.trim() === "") {
      setFilteredEntities(entities);
    } else {
      const filtered = entities.filter(entity =>
        entity.text.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredEntities(filtered);
    }
  }, [searchQuery, entities]);

  const groupedEntities = filteredEntities.reduce((acc, entity) => {
    if (!acc[entity.type]) {
      acc[entity.type] = [];
    }
    acc[entity.type].push(entity);
    return acc;
  }, {} as Record<string, Entity[]>);

  if (!isOpen) return null;

  return (
    <div className={cn(
      "fixed inset-y-0 right-0 z-50 w-80 bg-zinc-950 border-l border-zinc-800 shadow-lg transform transition-transform duration-300",
      isOpen ? "translate-x-0" : "translate-x-full",
      className
    )}>
      <Card className="h-full rounded-none border-0 bg-zinc-950">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
              <Tag className="w-5 h-5" />
              Entities
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0 hover:bg-zinc-800"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <Input
              placeholder="Search entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 bg-zinc-900 border-zinc-700 text-white"
            />
          </div>
        </CardHeader>
        
        <CardContent className="p-0">
          <ScrollArea className="h-[calc(100vh-140px)]">
            <div className="p-4 space-y-4">
              {Object.entries(groupedEntities).map(([type, typeEntities]) => {
                const config = entityTypeConfig[type as keyof typeof entityTypeConfig];
                const Icon = config.icon;
                
                return (
                  <div key={type} className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-zinc-400">
                      <Icon className="w-4 h-4" />
                      {type}s ({typeEntities.length})
                    </div>
                    <div className="space-y-1">
                      {typeEntities.map((entity, index) => (
                        <Button
                          key={`${entity.text}-${index}`}
                          variant="ghost"
                          className={cn(
                            "w-full justify-between h-auto p-2 hover:bg-zinc-800",
                            selectedEntity === entity.text && "bg-zinc-800"
                          )}
                          onClick={() => onEntitySelect(entity.text)}
                        >
                          <div className="flex items-center gap-2 flex-1 text-left">
                            <Badge
                              variant="secondary"
                              className={cn("text-xs", config.color)}
                            >
                              <Icon className="w-3 h-3 mr-1" />
                              {entity.text}
                            </Badge>
                          </div>
                          <span className="text-xs text-zinc-500">
                            {entity.linked_memories?.length || 0}
                          </span>
                        </Button>
                      ))}
                    </div>
                    {Object.keys(groupedEntities).indexOf(type) < Object.keys(groupedEntities).length - 1 && (
                      <Separator className="bg-zinc-800" />
                    )}
                  </div>
                );
              })}
              
              {filteredEntities.length === 0 && (
                <div className="text-center text-zinc-500 py-8">
                  <Tag className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No entities found</p>
                  {searchQuery && (
                    <p className="text-sm">Try a different search term</p>
                  )}
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
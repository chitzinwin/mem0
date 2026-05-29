import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { User, Building, Hash, Tag } from "lucide-react";

interface Entity {
  text: string;
  type: "PERSON" | "ORG" | "PROPER" | "COMPOUND";
  linked_memories?: string[];
}

interface EntityBadgeProps {
  entity: Entity;
  onClick?: (entityName: string) => void;
  className?: string;
}

const entityTypeConfig = {
  PERSON: {
    icon: User,
    variant: "secondary" as const,
    className: "bg-blue-500/20 text-blue-300 border-blue-500/30 hover:bg-blue-500/30",
  },
  ORG: {
    icon: Building,
    variant: "secondary" as const,
    className: "bg-green-500/20 text-green-300 border-green-500/30 hover:bg-green-500/30",
  },
  PROPER: {
    icon: Hash,
    variant: "secondary" as const,
    className: "bg-purple-500/20 text-purple-300 border-purple-500/30 hover:bg-purple-500/30",
  },
  COMPOUND: {
    icon: Tag,
    variant: "secondary" as const,
    className: "bg-orange-500/20 text-orange-300 border-orange-500/30 hover:bg-orange-500/30",
  },
};

export function EntityBadge({ entity, onClick, className }: EntityBadgeProps) {
  const config = entityTypeConfig[entity.type];
  const Icon = config.icon;

  return (
    <Badge
      variant={config.variant}
      className={cn(
        config.className,
        "cursor-pointer transition-all duration-200 hover:scale-105",
        className
      )}
      onClick={() => onClick?.(entity.text)}
    >
      <Icon className="w-3 h-3 mr-1" />
      {entity.text}
    </Badge>
  );
}

interface EntityListProps {
  entities: Entity[];
  onEntityClick?: (entityName: string) => void;
  maxDisplay?: number;
  className?: string;
}

export function EntityList({ 
  entities, 
  onEntityClick, 
  maxDisplay = 3,
  className 
}: EntityListProps) {
  if (!entities || entities.length === 0) {
    return null;
  }

  const displayEntities = entities.slice(0, maxDisplay);
  const remainingCount = entities.length - maxDisplay;

  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {displayEntities.map((entity, index) => (
        <EntityBadge
          key={`${entity.text}-${index}`}
          entity={entity}
          onClick={onEntityClick}
        />
      ))}
      {remainingCount > 0 && (
        <Badge variant="outline" className="text-xs text-zinc-400">
          +{remainingCount} more
        </Badge>
      )}
    </div>
  );
}
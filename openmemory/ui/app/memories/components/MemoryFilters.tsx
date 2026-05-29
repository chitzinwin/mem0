"use client";
import { Archive, Pause, Play, Search, Tag, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { FiTrash2 } from "react-icons/fi";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "@/store/store";
import { clearSelection } from "@/store/memoriesSlice";
import { useMemoriesApi } from "@/hooks/useMemoriesApi";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useRouter, useSearchParams } from "next/navigation";
import { debounce } from "lodash";
import { useEffect, useRef, useState } from "react";
import FilterComponent from "./FilterComponent";
import { EntitySidebar } from "@/components/shared/entity-sidebar";
import { clearFilters } from "@/store/filtersSlice";

export function MemoryFilters() {
  const dispatch = useDispatch();
  const selectedMemoryIds = useSelector(
    (state: RootState) => state.memories.selectedMemoryIds
  );
  const { deleteMemories, updateMemoryState, fetchMemories } = useMemoriesApi();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeFilters = useSelector((state: RootState) => state.filters.apps);

  const inputRef = useRef<HTMLInputElement>(null);
  const [entityBoost, setEntityBoost] = useState(false);
  const [entitySidebarOpen, setEntitySidebarOpen] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<string | undefined>();

  const handleDeleteSelected = async () => {
    try {
      await deleteMemories(selectedMemoryIds);
      dispatch(clearSelection());
    } catch (error) {
      console.error("Failed to delete memories:", error);
    }
  };

  const handleArchiveSelected = async () => {
    try {
      await updateMemoryState(selectedMemoryIds, "archived");
    } catch (error) {
      console.error("Failed to archive memories:", error);
    }
  };

  const handlePauseSelected = async () => {
    try {
      await updateMemoryState(selectedMemoryIds, "paused");
    } catch (error) {
      console.error("Failed to pause memories:", error);
    }
  };

  const handleResumeSelected = async () => {
    try {
      await updateMemoryState(selectedMemoryIds, "active");
    } catch (error) {
      console.error("Failed to resume memories:", error);
    }
  };

  // add debounce
  const handleSearch = debounce(async (query: string) => {
    const params = new URLSearchParams();
    if (query) params.set("search", query);
    if (entityBoost) params.set("entity_boost", "true");
    if (selectedEntity) params.set("entity_filter", selectedEntity);
    
    router.push(`/memories?${params.toString()}`);
  }, 500);

  const handleEntitySelect = (entityName: string) => {
    setSelectedEntity(entityName);
    setEntitySidebarOpen(false);
    
    // Update URL with entity filter
    const params = new URLSearchParams();
    const currentSearch = inputRef.current?.value;
    if (currentSearch) params.set("search", currentSearch);
    if (entityBoost) params.set("entity_boost", "true");
    params.set("entity_filter", entityName);
    
    router.push(`/memories?${params.toString()}`);
  };

  const clearEntityFilter = () => {
    setSelectedEntity(undefined);
    
    // Update URL without entity filter
    const params = new URLSearchParams();
    const currentSearch = inputRef.current?.value;
    if (currentSearch) params.set("search", currentSearch);
    if (entityBoost) params.set("entity_boost", "true");
    
    router.push(`/memories?${params.toString()}`);
  };

  useEffect(() => {
    // if the url has a search param, set the input value to the search param
    if (searchParams.get("search")) {
      if (inputRef.current) {
        inputRef.current.value = searchParams.get("search") || "";
        inputRef.current.focus();
      }
    }
  }, []);

  const handleClearAllFilters = async () => {
    dispatch(clearFilters());
    await fetchMemories(); // Fetch memories without any filters
  };

  const hasActiveFilters =
    activeFilters.selectedApps.length > 0 ||
    activeFilters.selectedCategories.length > 0;

  return (
    <div className="flex flex-col md:flex-row gap-4 mb-4">
      <div className="flex gap-4 flex-1">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <Input
            ref={inputRef}
            placeholder="Search memories..."
            className="pl-8 bg-zinc-950 border-zinc-800 max-w-[500px]"
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center space-x-2">
          <Switch
            id="entity-boost"
            checked={entityBoost}
            onCheckedChange={(checked) => {
              setEntityBoost(checked);
              // Re-trigger search with current input value
              if (inputRef.current?.value) {
                handleSearch(inputRef.current.value);
              }
            }}
          />
          <Label htmlFor="entity-boost" className="text-sm text-zinc-300 flex items-center gap-1">
            <Tag className="w-3 h-3" />
            Entity Boost
          </Label>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setEntitySidebarOpen(true)}
          className="bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border-zinc-700"
        >
          <Tag className="w-4 h-4 mr-1" />
          Entities
        </Button>
      </div>
      
      {/* Entity Filter Display */}
      {selectedEntity && (
        <div className="flex items-center gap-2 mt-2">
          <span className="text-sm text-zinc-400">Filtered by entity:</span>
          <div className="flex items-center gap-1 bg-zinc-800 rounded-md px-2 py-1">
            <Tag className="w-3 h-3 text-zinc-400" />
            <span className="text-sm text-white">{selectedEntity}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearEntityFilter}
              className="h-4 w-4 p-0 hover:bg-zinc-700 ml-1"
            >
              <X className="w-3 h-3" />
            </Button>
          </div>
        </div>
      )}
      <div className="flex gap-2">
        <FilterComponent />
        {hasActiveFilters && (
          <Button
            variant="outline"
            className="bg-zinc-900 text-zinc-300 hover:bg-zinc-800"
            onClick={handleClearAllFilters}
          >
            Clear Filters
          </Button>
        )}
        {selectedMemoryIds.length > 0 && (
          <>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  className="border-zinc-700/50 bg-zinc-900 hover:bg-zinc-800"
                >
                  Actions
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                className="bg-zinc-900 border-zinc-800"
              >
                <DropdownMenuItem onClick={handleArchiveSelected}>
                  <Archive className="mr-2 h-4 w-4" />
                  Archive Selected
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handlePauseSelected}>
                  <Pause className="mr-2 h-4 w-4" />
                  Pause Selected
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleResumeSelected}>
                  <Play className="mr-2 h-4 w-4" />
                  Resume Selected
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={handleDeleteSelected}
                  className="text-red-500"
                >
                  <FiTrash2 className="mr-2 h-4 w-4" />
                  Delete Selected
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
      </div>
      
      {/* Entity Sidebar */}
      <EntitySidebar
        isOpen={entitySidebarOpen}
        onClose={() => setEntitySidebarOpen(false)}
        onEntitySelect={handleEntitySelect}
        selectedEntity={selectedEntity}
      />
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   JOB SKILL PORTAL — D3.js BST Visualization
   ═══════════════════════════════════════════════════ */

class BSTVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.width = this.container.clientWidth;
        this.height = this.container.clientHeight || 500;
        this.nodeRadius = 22;
        this.tooltip = null;

        this.svg = d3.select(`#${containerId}`)
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height);

        // Add zoom behavior
        this.zoomGroup = this.svg.append('g');
        this.zoom = d3.zoom()
            .scaleExtent([0.2, 3])
            .on('zoom', (event) => {
                this.zoomGroup.attr('transform', event.transform);
            });
        this.svg.call(this.zoom);

        // Tooltip
        this.tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('display', 'none');

        this.linkGroup = this.zoomGroup.append('g').attr('class', 'links');
        this.nodeGroup = this.zoomGroup.append('g').attr('class', 'nodes');

        // Handle resize
        window.addEventListener('resize', () => {
            this.width = this.container.clientWidth;
            this.height = this.container.clientHeight || 500;
            this.svg.attr('width', this.width).attr('height', this.height);
        });
    }

    async loadTree(maxDepth = 6) {
        const data = await apiCall(`/api/bst/tree?max_depth=${maxDepth}`);
        if (data && data.tree) {
            this.renderTree(data.tree);
            return data.stats;
        }
        return null;
    }

    renderTree(treeData) {
        if (!treeData) {
            this.nodeGroup.selectAll('*').remove();
            this.linkGroup.selectAll('*').remove();
            return;
        }

        const root = d3.hierarchy(treeData, d => d.children);
        const treeLayout = d3.tree()
            .size([this.width - 100, this.height - 120])
            .separation((a, b) => (a.parent === b.parent ? 1.5 : 2));
        treeLayout(root);

        // Center the tree
        const initialTransform = d3.zoomIdentity
            .translate(50, 60)
            .scale(0.85);
        this.svg.call(this.zoom.transform, initialTransform);

        // Links
        const links = this.linkGroup.selectAll('.bst-link')
            .data(root.links(), d => `${d.source.data.name}-${d.target.data.name}`);

        links.exit().transition().duration(300).style('opacity', 0).remove();

        const linksEnter = links.enter()
            .append('path')
            .attr('class', 'bst-link')
            .attr('d', d3.linkVertical().x(d => d.x).y(d => d.y))
            .style('opacity', 0);

        links.merge(linksEnter)
            .transition().duration(500)
            .attr('d', d3.linkVertical().x(d => d.x).y(d => d.y))
            .style('opacity', 1);

        // Nodes
        const nodes = this.nodeGroup.selectAll('.bst-node')
            .data(root.descendants(), d => d.data.name);

        nodes.exit().transition().duration(300).style('opacity', 0).remove();

        const nodesEnter = nodes.enter()
            .append('g')
            .attr('class', 'bst-node')
            .attr('transform', d => `translate(${d.x},${d.y})`)
            .style('opacity', 0);

        nodesEnter.append('circle')
            .attr('r', 0)
            .transition().duration(500)
            .attr('r', this.nodeRadius);

        nodesEnter.append('text')
            .attr('dy', '0.35em')
            .text(d => {
                const name = d.data.name;
                return name.length > 10 ? name.substring(0, 9) + '…' : name;
            });

        // Frequency badge
        nodesEnter.append('text')
            .attr('class', 'freq-badge')
            .attr('dy', '-1.8em')
            .style('font-size', '8px')
            .style('fill', 'var(--accent-gold)')
            .text(d => d.data.frequency > 0 ? d.data.frequency : '');

        const allNodes = nodes.merge(nodesEnter);

        allNodes.transition().duration(500)
            .attr('transform', d => `translate(${d.x},${d.y})`)
            .style('opacity', 1);

        // Tooltip events
        const self = this;
        allNodes.on('mouseover', function (event, d) {
            self.tooltip
                .style('display', 'block')
                .style('left', (event.pageX + 15) + 'px')
                .style('top', (event.pageY - 10) + 'px')
                .html(`
                    <div class="tooltip-title">${d.data.name}</div>
                    <div class="tooltip-value">Frequency: ${d.data.frequency}</div>
                    <div class="tooltip-value">Jobs: ${d.data.job_count}</div>
                    <div class="tooltip-value">Depth: ${d.data.depth}</div>
                    ${d.data.truncated ? '<div class="tooltip-value" style="color:var(--accent-gold)">⚠ Subtree truncated</div>' : ''}
                `);
            d3.select(this).select('circle').classed('highlighted', true);
        })
            .on('mousemove', function (event) {
                self.tooltip
                    .style('left', (event.pageX + 15) + 'px')
                    .style('top', (event.pageY - 10) + 'px');
            })
            .on('mouseout', function () {
                self.tooltip.style('display', 'none');
                d3.select(this).select('circle').classed('highlighted', false);
            });
    }

    async highlightSearch(skill) {
        const result = await apiCall('/api/bst/search', {
            method: 'POST',
            body: JSON.stringify({ skill })
        });

        if (!result) return null;

        // Reset all highlights
        this.nodeGroup.selectAll('circle')
            .classed('search-path', false)
            .classed('highlighted', false);

        // Animate search path
        const path = result.path;
        for (let i = 0; i < path.length; i++) {
            await new Promise(resolve => setTimeout(resolve, 400));
            const skillName = path[i].skill;
            this.nodeGroup.selectAll('.bst-node')
                .filter(d => d && d.data && d.data.name === skillName)
                .select('circle')
                .classed('search-path', true);
        }

        return result;
    }

    async animateTraversal(type) {
        const result = await apiCall('/api/bst/traverse', {
            method: 'POST',
            body: JSON.stringify({ type, limit: 100 })
        });

        if (!result) return null;

        // Reset highlights
        this.nodeGroup.selectAll('circle')
            .classed('search-path', false)
            .classed('highlighted', false);

        // Animate each node in traversal order
        for (let i = 0; i < result.result.length; i++) {
            await new Promise(resolve => setTimeout(resolve, 200));
            const skillName = result.result[i].skill;
            this.nodeGroup.selectAll('.bst-node')
                .filter(d => d && d.data && d.data.name === skillName)
                .select('circle')
                .classed('highlighted', true);
        }

        return result;
    }

    resetHighlights() {
        this.nodeGroup.selectAll('circle')
            .classed('search-path', false)
            .classed('highlighted', false);
    }
}

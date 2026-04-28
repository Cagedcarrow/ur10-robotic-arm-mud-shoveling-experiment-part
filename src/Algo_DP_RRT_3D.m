function result = Algo_DP_RRT_3D(startNode, goalNode, obs_matrix_3d, params)
% =========================================================================
% Function: Algo_DP_RRT_3D 
% Description: 抹泥机械臂专属：三维空间下的动态引力势场与自适应步长 RRT 算法
% 核心特征严格对标 2D 逻辑:
%   1. 动态概率偏置 Pg(T_c) 逃逸 3D 局部极小值
%   2. 融合 3D 引力势场引导方向 (动态 rho)
%   3. 基于 3D 异构最短距离 d_min 的自适应扩展步长 lambda(d_min)
% =========================================================================

    % 1. 提取超参数
    maxIter    = params.maxIter;
    goalRadius = params.goalRadius;
    xMin = params.limits(1); xMax = params.limits(2);
    yMin = params.limits(3); yMax = params.limits(4);
    zMin = params.limits(5); zMax = params.limits(6);
    visualize  = params.visualize;
    
    % DP-RRT 核心创新超参数
    lambda_max = params.lambda_max; 
    lambda_min = params.lambda_min; 
    d_safe     = params.d_safe;     
    rho_init   = params.rho;        
    Pg_init    = 0.25;              
    
    % 初始化动态变量
    fail_count = 0;                 
    
    % 初始化数据结构 [x, y, z, parent_idx, cost]
    tree = [startNode, 0, 0]; 
    isReached = false;
    finalNodeIdx = -1;
    
    tic; 
    for iter = 1:maxIter
        
        % =================================================================
        % 核心 1: 概率与 3D 引力的双重指数衰减机制
        % =================================================================
        Pg_current  = Pg_init * exp(-0.5 * fail_count);
        rho_current = rho_init * exp(-0.5 * fail_count); 
        
        % 3D 动态概率采样
        if rand() < Pg_current
            q_rand = goalNode;
        else
            q_rand = [xMin + rand()*(xMax - xMin), ...
                      yMin + rand()*(yMax - yMin), ...
                      zMin + rand()*(zMax - zMin)];
        end
        
        % 3D 最近邻搜索
        distances = sqrt((tree(:,1) - q_rand(1)).^2 + ...
                         (tree(:,2) - q_rand(2)).^2 + ...
                         (tree(:,3) - q_rand(3)).^2);
        [~, min_idx] = min(distances);
        q_near = tree(min_idx, 1:3);
        
        % 3D 向量合成 (随机探索向量 vs 目标引力向量)
        v_rand = (q_rand - q_near);
        if norm(v_rand) > 0; v_rand = v_rand / norm(v_rand); end
        
        v_goal = (goalNode - q_near);
        if norm(v_goal) > 0; v_goal = v_goal / norm(v_goal); end
        
        if norm(q_rand - goalNode) > 1e-3
            v_new = (1 - rho_current) * v_rand + rho_current * v_goal;
        else
            v_new = v_goal; 
        end
        v_new = v_new / norm(v_new);
        
        % =================================================================
        % 核心 2: 3D 空间自适应步长反馈
        % =================================================================
        d_min = compute_3D_dmin_hetero(q_near, obs_matrix_3d);
        
        if d_min >= d_safe
            lambda_current = lambda_max;
        else
            kappa = 0.08; 
            numerator = exp(kappa * d_min) - 1;
            denominator = exp(kappa * d_safe) - 1;
            lambda_current = lambda_min + (lambda_max - lambda_min) * (numerator / denominator);
        end
        
        % 3D 步长扩展
        q_new = q_near + lambda_current * v_new;
        
        % 3D 越界保护
        if q_new(1)<xMin || q_new(1)>xMax || q_new(2)<yMin || q_new(2)>yMax || q_new(3)<zMin || q_new(3)>zMax
            fail_count = fail_count + 1;
            continue;
        end
        
        % =================================================================
        % 核心 3: 3D 碰撞检测与状态机恢复机制
        % =================================================================
        if ~checkCollision_3D(q_near, q_new, obs_matrix_3d)
            % 成功生长时：缓慢降低失败计数，模拟物理势场中的缓慢退避与恢复
            fail_count = max(0, fail_count - 2); 
            
            cost = tree(min_idx, 5) + norm(q_new - q_near);
            tree = [tree; q_new, min_idx, cost];
            
            % 实时渲染 (DP-RRT 依然采用经典的蓝色主题)
            if visualize && mod(size(tree,1), 20) == 0 && isfield(params, 'ax')
                plot3(params.ax, [q_near(1), q_new(1)], [q_near(2), q_new(2)], [q_near(3), q_new(3)], ...
                      'Color', [0.2 0.6 0.9 0.5], 'LineWidth', 1.5);
                drawnow limitrate; 
            end
            
            % 3D 收敛判定
            if norm(q_new - goalNode) <= goalRadius
                isReached = true;
                finalNodeIdx = size(tree, 1);
                break;
            end
        else
            % 发生碰撞：累加失败次数触发双重衰减
            fail_count = fail_count + 1;
        end
    end
    runTime = toc;

    % 路径回溯提取
    path = [];
    pathLength = inf;
    if isReached
        path = tree(finalNodeIdx, 1:3);
        curr_idx = finalNodeIdx;
        while curr_idx > 1
            curr_idx = tree(curr_idx, 4); % 第4列是 parent_idx
            path = [tree(curr_idx, 1:3); path];
        end
        pathLength = tree(finalNodeIdx, 5); % 第5列是 cost
        
        if visualize && isfield(params, 'ax')
            plot3(params.ax, path(:,1), path(:,2), path(:,3), 'b-', 'LineWidth', 3.5);
            drawnow;
        end
    end
    
    result.path = path;
    result.tree = tree;
    result.runTime = runTime;
    result.iter = iter;
    result.isReached = isReached;
    result.pathLength = pathLength;
end

%% =========================================================================
% 本地核心算子：3D 异构环境全局最短距离计算
% 功能：计算空间中任意一点到所有球体、圆柱体表面的确切最短几何距离
% =========================================================================
function d_min = compute_3D_dmin_hetero(pt, obs_matrix_3d)
    d_min = inf;
    px = pt(1); py = pt(2); pz = pt(3);
    
    for i = 1:size(obs_matrix_3d, 1)
        type = obs_matrix_3d(i, 1);
        switch type
            case 1 % 球体 (Sphere)
                cx = obs_matrix_3d(i, 2); cy = obs_matrix_3d(i, 3); cz = obs_matrix_3d(i, 4);
                r  = obs_matrix_3d(i, 5);
                d = max(0, sqrt((px - cx)^2 + (py - cy)^2 + (pz - cz)^2) - r);
                
            case 2 % 圆柱体 (Cylinder - Z 轴对齐)
                cx = obs_matrix_3d(i, 2); cy = obs_matrix_3d(i, 3); 
                r  = obs_matrix_3d(i, 4);
                z_min = obs_matrix_3d(i, 5); z_max = obs_matrix_3d(i, 6);
                
                % 1. 水平面 (XY) 内到圆柱体侧面的极小距离
                d_xy = sqrt((px - cx)^2 + (py - cy)^2);
                d_r = max(0, d_xy - r);
                
                % 2. 垂直面 (Z) 内到圆柱体上下底面的极小距离
                if pz < z_min
                    d_z = z_min - pz;
                elseif pz > z_max
                    d_z = pz - z_max;
                else
                    d_z = 0; % Z轴高度处于圆柱体范围内
                end
                
                % 3. 三维空间正交距离合成
                d = sqrt(d_r^2 + d_z^2);
        end
        
        % 捕捉全局极小值
        if d < d_min
            d_min = d; 
        end
    end
end